# backend/app/Routers/api.py

from Config.logger import setup_logging
from backend.app.Services.security_service import oauth2_scheme
from backend.app.Services.user_service import soft_delete_user
from Config.Config import settings
from Config.imports import (JSONResponse, datetime, AsyncSession, update,
	APIRouter, Depends, HTTPException, status, timedelta, CryptContext,
	Form, secrets, Request)
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

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user_action(
		nickname: str = Form(...),
		email: str = Form(...),
		password: str = Form(...),
		session: AsyncSession = Depends(get_async_session)
):
	try:
		existing_user = await user_service.get_user_by_email(session, email)
		if existing_user:
			log.warning(f"[AUTH][REGISTER] Attempt to register existing email: {email}")
			raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")

		new_user = await user_service.create_user(
			session=session,
			nickname=nickname,
			email=email,
			password=password
		)

		verification_token = security_service.create_verification_token(new_user.id)
		success = await mail_service.send_verification_email(
			user_email=new_user.email,
			verification_token=verification_token
		)

		if not success:
			return {
				"message": "Регистрация успешна, но ошибка отправки письма.",
				"resend_url": f"{settings.API_V1_STR}/auth/resend-verification/{new_user.id}"
			}

		log.info(f"[AUTH][REGISTER] Success for {email} (ID: {new_user.id})")
		return {"message": "Регистрация успешна! Письмо отправлено."}

	except HTTPException as e:
		log.warning(f"HTTP Error in register_user_action: {e.status_code} - {e.detail}")
		# ВАЖНО: Возвращаем объект error, чтобы catch сработал во фронте
		return {"error": e.detail}
	except Exception as e:
		log.error(f"Critical server error during user registration for email '{email}'", exc_info=True)
		return {"error": "Непредвиденная ошибка сервера. Администраторы уведомлены."}

@router.post("/login", response_model=dict)
async def login_for_access_token(
		request: Request,
		email: str = Form(...),
		password: str = Form(...),
		session: AsyncSession = Depends(get_async_session)
):
	log.info(f"[AUTH][LOGIN] Attempt for {email} from {request.client.host}")
	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	try:
		# 1. Проверка существования аккаунта
		user_record = await user_service.get_user_by_email(session, email)
		if not user_record:
			log.warning(f"[AUTH][FAILED] Account does not exist for {email}")
			return {"error": "Аккаунт не найден."}

		# 2. Аутентификация (проверка пароля)
		user = await user_service.authenticate_user(session, email, password)
		if not user or not user.is_active:
			log.warning(f"[AUTH][FAILED] Invalid credentials or inactive account for {email}")
			return {"error": "Неверный пароль."}

		# 3. Проверка подтверждения почты
		if not user.is_email_verified:
			log.warning(f"[AUTH][FORBIDDEN] Unverified email attempt for {email}")
			return {
				"error": "Необходимо подтвердить адрес электронной почты.",
				"action": "verify_email"
			}
		# Дополнительная проверка
		if not getattr(user, 'is_active', False):
			log.critical(f"[AUTH][RACE_CONDITION] Inactive user reached token generation for {email}")
			return {"error": "Доступ запрещен."}

		if not isinstance(user, User):
			log.critical(f"[AUTH][TYPE_MISMATCH] Non-User object passed to create_jwt_pair for {email}")
			return {"error": "Непредвиденная ошибка сервера аутентификации."}

		tokens = await security_service.create_jwt_pair(
			user_obj_or_id=user,
			expires_delta=access_token_expires
		)

		log.info(f"[AUTH][SUCCESS] Login successful for {email} (ID: {user.id})")
		return {
			"access_token": tokens["access_token"],
			"token_type": "bearer",
			"refresh_token": tokens["refresh_token"]
		}
	except PermissionError as e:
		log.warning(f"[AUTH][BLOCKED] Account state issue during login for {email}: {e}")
		return {"error": "Доступ запрещен."}
	except Exception as e:
		log.error(f"Critical error during login for '{email}'", exc_info=True)
		return {"error": "Непредвиденная ошибка сервера."}

@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_async_session)):
	payload = security_service.verify_token(token, purpose="email_verification")
	user_id: str = payload.get("sub")
	if not user_id:
		raise HTTPException(status_code=400, detail="Неверный токен.")

	success = await user_service.verify_email(session, user_id)
	if not success:
		raise HTTPException(status_code=404, detail="Пользователь не найден.")

	return JSONResponse(content={"message": "Email успешно подтвержден."}, status_code=200)

@router.post("/logout")
async def logout(
		token: str = Depends(security_service.oauth2_scheme),
		session: AsyncSession = Depends(get_async_session)
):
	await security_service.blacklist_token(token)
	return {"message": "Выход выполнен успешно"}

@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
		password: str = Form(...),
		permanent: bool = False,
		db: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(oauth2_scheme)
):
	# 1. Сверка пароля
	if not pwd_context.verify(password, current_user.password_hash):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Неверный пароль.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	# 2. Выполнение мягкого удаления
	success = await soft_delete_user(db, current_user.id)

	if not success:
		raise HTTPException(status_code=404, detail="Пользователь не найден или уже удален.")

	# 3. Принудительная инвалидация всех активных сессий (Logout everywhere)
	new_session_token = secrets.token_urlsafe(64)

	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)

	await db.execute(stmt)
	await db.commit()

	log.info(f"[ACCOUNT][DELETED] Account {current_user.id} ({current_user.email}) marked as deleted.")
	return None