# backend/app/Routers/api.py

from backend.app.Services.security_service import oauth2_scheme
from backend.app.Services.user_service import soft_delete_user
from Config.Config import settings
from Config.imports import (JSONResponse, datetime, AsyncSession, OAuth2PasswordRequestForm, update,
					APIRouter, Depends, HTTPException, status, timedelta, SecurityScopes, CryptContext,
					Form, secrets)
from backend.app.database.database import get_async_session
from backend.app.database.models.core.user import User
from backend.app.database.models.core.auth import UserRole
from backend.app.enums.enums_BD import SystemRole
from backend.app.Services import security_service, user_service, mail_service

router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- POST: Обработка нажатия кнопки "Зарегистрироваться" ---
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

		# Возвращаем сообщение для вставки в #message-box
		return {
			"message": "Регистрация успешна! Письмо отправлено."
		}

	except HTTPException as e:
		# Прокидываем ошибки FastAPI как текст для верстки
		return {"error": e.detail}
	except Exception as e:
		print(f"[REGISTRATION ERROR]: {e}")
		return {"error": "Непредвиденная ошибка сервера."}

@router.post("/login", response_model=dict)
async def login_for_access_token(
		form_data: OAuth2PasswordRequestForm = Depends(),
		session: AsyncSession = Depends(get_async_session)
):
	"""
	Стандартный вход по паролю. Возвращает JWT-токены.
	"""
	user = await user_service.authenticate_user(session, form_data.username, form_data.password)
	if not user or not user.is_active:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Некорректные учетные данные",
			headers={"WWW-Authenticate": "Bearer"},
		)

	if not user.is_email_verified:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Необходимо подтвердить адрес электронной почты."
		)

	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
	tokens = await security_service.create_jwt_pair(user.id, expires_delta=access_token_expires)

	return {
		"access_token": tokens["access_token"],
		"token_type": "bearer",
		"refresh_token": tokens["refresh_token"]
	}

@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_async_session)):
	"""
	Активация аккаунта по ссылке из письма.
	"""
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
	"""
	Добавление токена в черный список (через Redis) или инвалидация сессии.
	Согласно ТЗ, при смене пароля мы будем обновлять active_session_token у пользователя.
	"""
	await security_service.blacklist_token(token)
	return {"message": "Выход выполнен успешно"}

@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
		password: str = Form(...), # Используем Form, так как шлем данные формы или x-www-form-urlencoded
		permanent: bool = False,
		db: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(oauth2_scheme)
):
	"""
	Удаление собственного аккаунта.
	- По умолчанию выполняется Soft Delete (деактивация).
	- Все связанные данные будут удалены каскадно при физическом удалении записи.
	"""

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
	# Это критически важно по ТЗ (поле active_session_token)
	new_session_token = secrets.token_urlsafe(64)

	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)

	# ВАЖНО: В SQLAlchemy 2.x execute возвращает Result, его нужно зафиксировать
	await db.execute(stmt)
	await db.commit()

	return None