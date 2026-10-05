# backend/app/Routers/api.py

from Config.logger import setup_logging
from backend.app.Services.security_service import (create_verification_token, verify_token)
from backend.app.Services.user_service import (soft_delete_user, get_current_user)
from Config.Config import settings
from Config.imports import (JSONResponse, datetime, AsyncSession, update, UUID, RedirectResponse,
                            APIRouter, Depends, HTTPException, status, timedelta, CryptContext,
                            Form, secrets, Request, CsrfProtect)
from backend.app.database.database import get_async_session
from backend.app.database.models.core.user import User
from backend.app.Services import security_service, user_service
from backend.app.Services.mail_service import mail_service
from backend.app.schemas.auth import RegisterRequest

router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)

log = setup_logging(app_name="WebDND_Site")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user_action(
		request: Request,
		data: RegisterRequest,
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
	log.info(f"[AUTH][REGISTER] Attempt for {data.email}")
	try:
		existing_user = await user_service.get_user_by_email(session, data.email)
		if existing_user:
			log.warning(f"[AUTH][REGISTER] Duplicate attempt blocked for {data.email} (ID: {existing_user.id})")
			return JSONResponse(
				status_code=409,
				content={"error": "Пользователь с таким email уже существует"}
			)

		new_user = await user_service.create_user(
			session=session,
			nickname=data.nickname,
			email=data.email,
			password=data.password
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

		log.info(f"[AUTH][REGISTER] Success for {data.email} (ID: {new_user.id})")
		return JSONResponse(
			status_code=201,
			content={"message": "Регистрация успешна! Письмо отправлено."}
		)

	except Exception as e:
		log.error(f"Critical server error during user registration for email '{data.email}'", exc_info=True)
		return JSONResponse(
			status_code=500,
			content={"error": "Непредвиденная ошибка сервера. Администраторы уведомлены."}
		)

@router.post("/login", response_model=dict)
async def login_for_access_token(
		request: Request,
		email: str = Form(...),
		password: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
	log.info(f"[AUTH][LOGIN] Attempt for {email} from {request.client.host}")
	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	try:
		user_record = await user_service.get_user_by_email(session, email)
		if not user_record:
			log.warning(f"[AUTH][FAILED] Account does not exist for {email}")
			return JSONResponse(status_code=401, content={"error": "Аккаунт не найден."
				, "action": "account_not_found"})

		user = await user_service.authenticate_user(session, email, password)
		if not user or not user.is_active:
			log.warning(f"[AUTH][FAILED] Invalid credentials or inactive account for {email}")
			return JSONResponse(status_code=401, content={"error": "Неверный пароль."})

		if not user.is_email_verified:
			log.warning(f"[AUTH][FORBIDDEN] Unverified email attempt for {email}")
			return JSONResponse(status_code=401, content={
				"error": "Необходимо подтвердить адрес электронной почты.",
				"action": "verify_email"
			})

		new_session_token = secrets.token_urlsafe(64)

		tokens = await security_service.create_jwt_pair(
			user_obj_or_id=user,
			expires_delta=access_token_expires,
			session_token=new_session_token
		)

		log.info(f"[AUTH][SUCCESS] Login successful for {email} (ID: {user.id})")

		response = JSONResponse(content={
			"access_token": tokens["access_token"],
			"token_type": "bearer",
			"refresh_token": tokens["refresh_token"]
		})

		response.set_cookie(
			key="access_token",
			value=tokens["access_token"],
			httponly=True,
			samesite="lax",
			path="/",
			max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
			secure=settings.SECURE_COOKIES
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
		# Было: raise HTTPException(status_code=400, ...) — пользователь видел голый JSON.
		# Теперь отправляем на страницу входа с пометкой об ошибке в query-параметре.
		return RedirectResponse(url="/login?verify=invalid", status_code=status.HTTP_303_SEE_OTHER)

	success = await user_service.verify_email(session, user_id)
	if not success:
		log.error(f"[AUTH][VERIFY] User ID {user_id} not found in DB.")
		return RedirectResponse(url="/login?verify=notfound", status_code=status.HTTP_303_SEE_OTHER)

	log.info(f"[AUTH][VERIFY] Email verified for user ID {user_id}.")
	# Было: JSONResponse({"message": "Email успешно подтвержден."}) — теперь переход на вход.
	return RedirectResponse(url="/login?verify=success", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/resend-verification/{user_id}", response_model=dict)
async def resend_verification_email(
		user_id: UUID,
		session: AsyncSession = Depends(get_async_session)
):
	"""Повторная отправка письма подтверждения почты."""
	target_user = await user_service.get_user_by_id(session, user_id)

	if not target_user:
		raise HTTPException(status_code=404, detail="Пользователь не найден.")

	if target_user.is_email_verified:
		return JSONResponse(
			status_code=200,
			content={"message": "Почта уже подтверждена, письмо не отправлено."}
		)

	verification_token = create_verification_token(target_user.id)

	try:
		await mail_service.send_verification_email(
			user_email=target_user.email,
			verification_token=verification_token
		)
	except Exception as e:
		log.error(f"[AUTH][RESEND] Failed to send verification email to {target_user.email}: {e}")
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Не удалось отправить письмо. Попробуйте позже."
		)

	log.info(f"[AUTH][RESEND] Verification email re-sent for {target_user.id}")
	return JSONResponse(
		status_code=200,
		content={"message": "Письмо с подтверждением отправлено повторно."}
	)

@router.post("/logout")
async def logout(
		request: Request,
		current_user: User = Depends(get_current_user),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=None, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	response = JSONResponse(content={"message": "Выход выполнен успешно"})
	response.delete_cookie(key="access_token", path="/")
	response.delete_cookie(key="refresh_token", path="/")
	response.headers["HX-Redirect"] = "/login"

	log.info(f"[AUTH][LOGOUT] Session invalidated and cookies cleared for {current_user.id}.")
	return response

@router.post("/delete-account")
async def delete_account(
		request: Request,
		password: str = Form(...),
		permanent: bool = Form(False),
		db: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
		csrf_protect: CsrfProtect = Depends()
):
	"""Удаление аккаунта."""
	await csrf_protect.validate_csrf(request)

	if not current_user.password_hash:
		log.warning(f"[ACCOUNT][DELETE] No local password set (OAuth-only account) for {current_user.id}")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Для этого аккаунта не задан пароль (вход через соцсеть). Удаление по паролю недоступно.",
		)

	if not pwd_context.verify(password, current_user.password_hash):
		log.warning(f"[ACCOUNT][DELETE] Wrong password attempt for {current_user.id}")
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Неверный пароль.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	if permanent:
		await user_service.hard_delete_user(db, current_user.id)
		action_log = "Account permanently deleted."
	else:
		success = await soft_delete_user(db, current_user.id)
		if not success:
			log.error(f"[ACCOUNT][DELETE] Soft delete failed for {current_user.id}")
			raise HTTPException(status_code=404, detail="Пользователь не найден или уже удален.")
		action_log = "Account marked as deleted."

	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=None, updated_at=datetime.utcnow())
	)
	await db.execute(stmt)
	await db.commit()

	log.info(f"[ACCOUNT][DELETED] Account {current_user.id} processed. Action: {action_log}")

	response = JSONResponse(content={"message": "Аккаунт удалён."})
	response.delete_cookie(key="access_token", path="/")
	response.delete_cookie(key="refresh_token", path="/")
	response.headers["HX-Redirect"] = "/login"
	return response

@router.post("/refresh", response_model=dict)
async def refresh_access_token(
		request: Request,
		session: AsyncSession = Depends(get_async_session),
):
	"""Выдача новой пары токенов по refresh_token из cookie."""
	refresh_token = request.cookies.get("refresh_token")
	if not refresh_token:
		raise HTTPException(status_code=401, detail="Refresh-токен отсутствует.")

	try:
		payload = security_service.jwt.decode(
			refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
		)
	except security_service.JWTError:
		raise HTTPException(status_code=401, detail="Недействительный refresh-токен.")

	if payload.get("type") != "refresh":
		log.warning("[AUTH][REFRESH] Token with wrong type used as refresh.")
		raise HTTPException(status_code=401, detail="Недействительный refresh-токен.")

	user_id = payload.get("sub")
	token_sid = payload.get("sid")
	user = await user_service.get_user_by_id(session, user_id)

	if not user or not user.is_active or user.active_session_token != token_sid:
		log.warning(f"[AUTH][REFRESH] Session revoked or user inactive for {user_id}.")
		raise HTTPException(status_code=401, detail="Сессия завершена, войдите снова.")

	new_session_token = secrets.token_urlsafe(64)
	tokens = await security_service.create_jwt_pair(
		user_obj_or_id=user,
		session_token=new_session_token
	)

	stmt = (
		update(User)
		.where(User.id == user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	response = JSONResponse(content={"message": "Токен обновлён."})
	response.set_cookie(
		key="access_token", value=tokens["access_token"],
		httponly=True, samesite="lax", path="/",
		max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, secure=settings.SECURE_COOKIES
	)
	response.set_cookie(
		key="refresh_token", value=tokens["refresh_token"],
		httponly=True, samesite="lax", path="/",
		max_age=7 * 24 * 60 * 60, secure=settings.SECURE_COOKIES
	)
	log.info(f"[AUTH][REFRESH] Tokens refreshed for {user.id}")
	return response