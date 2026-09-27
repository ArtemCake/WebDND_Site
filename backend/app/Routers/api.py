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
from backend.app.schemas.auth import RegisterRequest, LoginRequest, UpdateProfileRequest, ChangePasswordRequest


router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)

log = setup_logging(app_name="WebDND_Site")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
csrf = CsrfProtect()

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user_action(
		# Используем готовую схему вместо набора полей Form
		data: RegisterRequest,
		session: AsyncSession = Depends(get_async_session)
):
	"""
	Регистрация нового пользователя.
	Входные данные строго валидируются схемой RegisterRequest до попадания в функцию.
	"""
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
		# Используем готовую схему
		data: LoginRequest,
		session: AsyncSession = Depends(get_async_session)
):
	"""
	Авторизация по паролю.
	Валидатор Pydantic проверил сложность пароля еще до вызова этой функции.
	"""
	log.info(f"[AUTH][LOGIN] Attempt for {data.email} from {request.client.host}")
	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	try:
		user_record = await user_service.get_user_by_email(session, data.email)
		if not user_record:
			log.warning(f"[AUTH][FAILED] Account does not exist for {data.email}")
			return JSONResponse(status_code=404, content={"error": "Аккаунт не найден."})

		user = await user_service.authenticate_user(session, data.email, data.password)
		if not user or not user.is_active:
			log.warning(f"[AUTH][FAILED] Invalid credentials or inactive account for {data.email}")
			return JSONResponse(status_code=401, content={"error": "Неверный пароль."})

		if not user.is_email_verified:
			log.warning(f"[AUTH][FORBIDDEN] Unverified email attempt for {data.email}")
			return JSONResponse(status_code=403, content={
				"error": "Необходимо подтвердить адрес электронной почты.",
				"action": "verify_email"
			})

		tokens = await security_service.create_jwt_pair(
			user_obj_or_id=user,
			expires_delta=access_token_expires
		)

		log.info(f"[AUTH][SUCCESS] Login successful for {data.email} (ID: {user.id})")

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
		log.warning(f"[AUTH][BLOCKED] Account state issue during login for {data.email}: {e}")
		return JSONResponse(status_code=403, content={"error": "Доступ запрещен."})
	except Exception as e:
		log.error(f"Critical error during login for '{data.email}'", exc_info=True)
		return JSONResponse(status_code=500, content={"error": "Непредвиденная ошибка сервера."})

# ... [роутеры /verify-email и /logout остаются без изменений, так как принимают query-параметры или токен]

@router.put("/profile/update", response_model=dict)
async def api_update_profile(
		# Для HTMX-форм оставляем ручной сбор данных через Form
		nickname: str = Form(...),
		email: EmailStr = Form(...),
		avatar: UploadFile | None = File(None),
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)
):
	"""
	Обновляет базовые данные профиля.
	Примечание: Так как запрос приходит от htmx через form-data, используем Form.
	Внутри сервиса должна быть повторная проверка уникальности email.
	"""
	try:
		# Собираем словарь вручную, чтобы передать в сервис слой
		profile_data = {"nickname": nickname, "email": email}

		updated_user = await update_user_profile(
			session=session,
			target_user=current_user,
			data=profile_data,
			avatar_file=avatar
		)

		return {"message": "Профиль успешно обновлен.", "avatar_url": updated_user.avatar_url}

	except ValueError as e:
		if "already exists" in str(e).lower():
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="Пользователь с таким адресом электронной почты уже существует."
			)
		raise
	except Exception as e:
		print(f"[PROFILE UPDATE ERROR] ID: {current_user.id}, Error: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Ошибка сервера при сохранении профиля."
		)

@router.post("/change-password", response_model=dict)
async def change_password_endpoint(
		# Здесь также используется Form, так как смена пароля обычно идет через форму
		current_password: str = Form(...),
		new_password: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)
):
	"""Смена пароля текущим пользователем."""

	# Ручная валидация сложности здесь может быть избыточной,
	# если вынести её в отдельный Middleware или Service Layer.
	# Но для единообразия можно создать мини-схему прямо тут:
	from pydantic import BaseModel

	class TempPwdSchema(BaseModel):
		current_password: str
		new_password: str

	validated = TempPwdSchema(current_password=current_password, new_password=new_password)

	success = await change_password(
		session=session,
		user=current_user,
		old_password=validated.current_password,
		new_password=validated.new_password
	)
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