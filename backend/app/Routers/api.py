# backend/app/Routers/api.py

from Config.logger import setup_logging
from backend.app.Services.security_service import oauth2_scheme, create_verification_token, verify_token, blacklist_token
from backend.app.Services.user_service import soft_delete_user, get_current_user, change_password, update_user_profile
from Config.Config import settings
from Config.imports import (JSONResponse, datetime, AsyncSession, update, CsrfProtect, File, Dict,
                            APIRouter, Depends, HTTPException, status, timedelta, CryptContext,
                            Form, secrets, Request, HTMLResponse, UploadFile)
from backend.app.database.database import get_async_session
from backend.app.database.models.core.user import User
from backend.app.Services import security_service, user_service
from backend.app.Services.mail_service import mail_service


router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)

log = setup_logging(app_name="WebDND_Site")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
csrf = CsrfProtect()  # Инициализация менеджера CSRF

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user_action(
		nickname: str = Form(...),
		email: str = Form(...),
		password: str = Form(...),
		session: AsyncSession = Depends(get_async_session)
):
	"""
	Регистрация нового пользователя.
	Фикс безопасности: Логирование попыток регистрации существующих почт до проверки БД вынесено внутрь try/except.
	"""
	log.info(f"[AUTH][REGISTER] Attempt for {email}")
	try:
		existing_user = await user_service.get_user_by_email(session, email)
		if existing_user:
			log.warning(f"[AUTH][REGISTER] Duplicate attempt blocked for {email} (ID: {existing_user.id})")
			return JSONResponse(
				status_code=409,
				content={"error": "Пользователь с таким email уже существует"}
			)

		new_user = await user_service.create_user(
			session=session,
			nickname=nickname,
			email=email,
			password=password
		)

		verification_token = create_verification_token(new_user.id)
		success = await mail_service.send_verification_email(
			user_email=new_user.email,
			verification_token=verification_token
		)

		if not success:
			log.error(f"[AUTH][MAIL_FAIL] Failed to send verification for {new_user.id}")
			return JSONResponse(
				status_code=201,
				content={
					"message": "Регистрация успешна, но ошибка отправки письма.",
					"resend_url": f"{settings.API_V1_STR}/auth/resend-verification/{new_user.id}"
				}
			)

		log.info(f"[AUTH][REGISTER] Success for {email} (ID: {new_user.id})")
		return JSONResponse(
			status_code=201,
			content={"message": "Регистрация успешна! Письмо отправлено."}
		)

	except Exception as e:
		log.error(f"Critical server error during user registration for email '{email}'", exc_info=True)
		return JSONResponse(
			status_code=500,
			content={"error": "Непредвиденная ошибка сервера. Администраторы уведомлены."}
		)

@router.post("/login", response_model=dict)
async def login_for_access_token(
		request: Request,
		email: str = Form(...),
		password: str = Form(...),
		session: AsyncSession = Depends(get_async_session)
):
	"""
	Авторизация по паролю.
	Фиксы безопасности:
	1. Проверка активности и верификации ДО генерации токена.
	2. Использование HttpOnly кук + SameSite=Lax.
	3. Принудительная инвалидация старых сессий при входе.
	"""
	log.info(f"[AUTH][LOGIN] Attempt for {email} from {request.client.host}")
	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	try:
		user_record = await user_service.get_user_by_email(session, email)
		if not user_record:
			log.warning(f"[AUTH][FAILED] Account does not exist for {email}")
			return JSONResponse(status_code=404, content={"error": "Аккаунт не найден."})

		user = await user_service.authenticate_user(session, email, password)
		if not user or not user.is_active:
			log.warning(f"[AUTH][FAILED] Invalid credentials or inactive account for {email}")
			return JSONResponse(status_code=401, content={"error": "Неверный пароль."})

		if not user.is_email_verified:
			log.warning(f"[AUTH][FORBIDDEN] Unverified email attempt for {email}")
			return JSONResponse(status_code=403, content={
				"error": "Необходимо подтвердить адрес электронной почты.",
				"action": "verify_email"
			})

		# Генерация пары токенов только после всех проверок
		tokens = await security_service.create_jwt_pair(
			user_obj_or_id=user,
			expires_delta=access_token_expires
		)

		log.info(f"[AUTH][SUCCESS] Login successful for {email} (ID: {user.id})")

		response = JSONResponse(content={
			"access_token": tokens["access_token"],
			"token_type": "bearer",
			"refresh_token": tokens["refresh_token"]
		})

		# Установка безопасных кук
		response.set_cookie(
			key="access_token",
			value=tokens["access_token"],
			httponly=True,
			samesite="lax",
			path="/",
			max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
			secure=settings.SECURE_COOKIES  # Требует HTTPS в проде
		)
		response.set_cookie(
			key="refresh_token",
			value=tokens["refresh_token"],
			httponly=True,
			samesite="lax",
			path="/",
			max_age=7 * 24 * 60 * 60,
			secure=settings.SECURE_COOKIES
		)

		# Инвалидация предыдущих активных сессий (защита от угона сессии)
		new_session_token = secrets.token_urlsafe(64)
		stmt = (
			update(User)
			.where(User.id == user.id)
			.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
		)
		await session.execute(stmt)
		await session.commit()

		return response

	except PermissionError as e:
		log.warning(f"[AUTH][BLOCKED] Account state issue during login for {email}: {e}")
		return JSONResponse(status_code=403, content={"error": "Доступ запрещен."})
	except Exception as e:
		log.error(f"Critical error during login for '{email}'", exc_info=True)
		return JSONResponse(status_code=500, content={"error": "Непредвиденная ошибка сервера."})

@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_async_session)):
	"""Подтверждение адреса почты."""
	payload = verify_token(token, purpose="email_verification")
	user_id: str = payload.get("sub") if payload else None

	if not user_id:
		log.warning("[AUTH][VERIFY] Invalid or expired token provided.")
		raise HTTPException(status_code=400, detail="Неверный или просроченный токен.")

	success = await user_service.verify_email(session, user_id)
	if not success:
		log.error(f"[AUTH][VERIFY] User ID {user_id} not found in DB.")
		raise HTTPException(status_code=404, detail="Пользователь не найден.")

	log.info(f"[AUTH][VERIFY] Email verified for user ID {user_id}.")
	return JSONResponse(content={"message": "Email успешно подтвержден."}, status_code=200)

@router.post("/logout")
async def logout(
		token: str = Depends(oauth2_scheme),
		session: AsyncSession = Depends(get_async_session)
):
	"""
	Выход из системы.
	Фикс безопасности: Добавлена очистка клиентских кук через Set-Cookie с истекшим сроком.
	"""
	await security_service.blacklist_token(token) # Помечаем Access Token как недействительный

	response = JSONResponse(content={"message": "Выход выполнен успешно"})

	# Удаляем куки на клиенте
	response.delete_cookie(key="access_token", path="/")
	response.delete_cookie(key="refresh_token", path="/")

	log.info(f"[AUTH][LOGOUT] Token invalidated and cookies cleared.")
	return response

@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
		password: str = Form(...),
		permanent: bool = False,
		db: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(oauth2_scheme)
):
	"""
	Удаление аккаунта.
	Фикс безопасности: Перед удалением принудительно инвалидируются все активные сессии во всей инфраструктуре.
	"""
	# 1. Сверка пароля перед критическим действием
	if not pwd_context.verify(password, current_user.password_hash):
		log.warning(f"[ACCOUNT][DELETE] Wrong password attempt for {current_user.id}")
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Неверный пароль.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	# 2. Выполнение удаления
	if permanent:
		await user_service.hard_delete_user(db, current_user.id)
		action_log = "Account permanently deleted."
	else:
		success = await soft_delete_user(db, current_user.id)
		if not success:
			log.error(f"[ACCOUNT][DELETE] Soft delete failed for {current_user.id}")
			raise HTTPException(status_code=404, detail="Пользователь не найден или уже удален.")
		action_log = "Account marked as deleted."

	# 3. Принудительная инвалидация всех активных сессий (Logout everywhere)
	# Это гарантирует, что украденные ранее токены перестанут работать мгновенно
	new_session_token = secrets.token_urlsafe(64)
	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)
	await db.execute(stmt)
	await db.commit()

	log.info(f"[ACCOUNT][DELETED] Account {current_user.id} ({current_email}) processed. Action: {action_log}")
	return None

@router.put("/profile/update", response_model=dict)
async def update_profile(
		data: Dict = Form(...),
		avatar: UploadFile | None = File(None),
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(oauth2_scheme)
):
	"""Обновление профиля текущего пользователя."""
	try:
		updated_user = await update_user_profile(session, current_user, data, avatar)
		log.info(f"[PROFILE] Updated profile for user {updated_user.id}")
		return {"message": "Профиль успешно обновлен.", "user": updated_user.model_dump()}
	except ValueError as e:
		log.warning(f"[PROFILE] Update conflict for {current_user.id}: {str(e)}")
		raise HTTPException(status_code=409, detail=str(e))
	except Exception as e:
		log.error(f"[PROFILE] Unexpected error updating {current_user.id}", exc_info=True)
		raise HTTPException(status_code=500, detail="Ошибка сохранения данных.")

@router.post("/change-password", response_model=dict)
async def change_password_endpoint(
		current_password: str = Form(...),
		new_password: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(oauth2_scheme)
):
	"""Смена пароля текущим пользователем."""
	success = await change_password(session, current_user, current_password, new_password)
	if not success:
		log.warning(f"[SECURITY] Password change failed for {current_user.id} - wrong old pass.")
		raise HTTPException(status_code=401, detail="Текущий пароль неверен.")

	# После смены пароля сбрасываем активную сессию
	new_session_token = secrets.token_urlsafe(64)
	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	log.info(f"[SECURITY] Password changed successfully for {current_user.id}. Session rotated.")
	return {"message": "Пароль успешно изменен."}