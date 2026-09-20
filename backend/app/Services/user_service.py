from Config.Config import settings
from backend.app.Services.security_service import oauth2_scheme
from backend.app.database.models.core.user import User
from Config.imports import (Optional, AsyncSession, select, Depends, HTTPException, status,
	jwt, JWTError, datetime, ValidationError, Dict, Any, UploadFile, update, CryptContext)
from backend.app.database.database import get_async_session


# ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ ДЛЯ ХЕШИРОВАНИЯ
# Схема должна строго совпадать с той, что указана в api.py
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
	result = await session.execute(select(User).where(User.email == email))
	return result.scalar_one_or_none()

async def create_user(session: AsyncSession, nickname: str, email: str, password: str) -> User:
	hashed_pw = pwd_context.hash(password)  # Используем общий контекст
	user = User(
		email=email,
		nickname=nickname,
		password_hash=hashed_pw,
		is_email_verified=False
	)
	session.add(user)
	await session.commit()
	await session.refresh(user)
	return user

async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
	"""
	Проверяет существование пользователя и валидность пароля.
	ВАЖНО: Теперь использует общую схему argon2.
	"""
	user = await get_user_by_email(session, email)
	if not user:
		return None

	# Убираем создание нового экземпляра Passlib!
	try:
		# Argon2 автоматически определит параметры соли из строки хеша
		pwd_context.verify(password, user.password_hash)
		return user
	except Exception as e:
		# Логируем неудачную попытку входа для безопасности
		from Config.logger import setup_logging
		log = setup_logging(app_name="WebDND_Site")
		log.warning(f"[AUTH][PASSWORD_VERIFY_FAILED] For {email}: {str(e)}")
		return None

async def verify_email(session: AsyncSession, user_id: str) -> bool:
	result = await session.execute(select(User).where(User.id == user_id))
	user = result.scalar_one_or_none()
	if user and not user.is_email_verified:
		user.is_email_verified = True
		await session.commit()
		return True
	return False

async def soft_delete_user(session: AsyncSession, user_id: str) -> bool:
	result = await session.execute(select(User).where(User.id == user_id))
	user = result.scalar_one_or_none()

	if not user or user.is_active is False:
		return False

	stmt = (
		update(User)
		.where(User.id == user_id)
		.values(is_active=False, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()
	return True

async def hard_delete_user(session: AsyncSession, user_id: str) -> None:
	result = await session.execute(select(User).where(User.id == user_id))
	user = result.scalar_one_or_none()
	if user:
		await session.delete(user)
		await session.commit()

async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
	result = await session.execute(select(User).where(User.id == user_id))
	return result.scalar_one_or_none()

async def get_current_user(
		token: str = Depends(oauth2_scheme),
		session: AsyncSession = Depends(get_async_session)
) -> User:
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)

	try:
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
		user_id: str = payload.get("sub")
		if user_id is None:
			raise credentials_exception

		exp_timestamp = payload.get("exp")
		if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
			raise credentials_exception

	except (JWTError, ValidationError):
		raise credentials_exception

	user = await get_user_by_id(session, user_id)
	if user is None or not user.is_active:
		raise credentials_exception

	return user

async def update_user_profile(
		session: AsyncSession,
		target_user: User,
		data: Dict[str, Any],
		avatar_file: UploadFile | None = None
) -> User:
	needs_commit = False

	new_nickname = data.get("nickname")
	new_email = data.get("email")

	if new_nickname and new_nickname != target_user.nickname:
		target_user.nickname = new_nickname
		needs_commit = True

	if new_email and new_email != target_user.email:
		existing_user = await get_user_by_email(session, new_email)
		if existing_user and existing_user.id != target_user.id:
			raise ValueError("Email already exists")

		target_user.email = new_email
		target_user.is_email_verified = False
		needs_commit = True

	if avatar_file:
		# Заглушка загрузки файлов
		target_user.avatar_url = f"/data/avatars/{target_user.id}/{avatar_file.filename}"
		needs_commit = True

	if needs_commit:
		target_user.updated_at = datetime.utcnow()
		await session.commit()
		await session.refresh(target_user)

	return target_user

async def change_password(
		session: AsyncSession,
		user: User,
		old_password: str,
		new_password: str
) -> bool:
	"""
	Меняет пароль и инвалидацию сессий согласно ТЗ п.38.
	"""
	try:
		pwd_context.verify(old_password, user.password_hash)
	except Exception:
		return False

	# Обновляем хеш новым алгоритмом/солью
	user.password_hash = pwd_context.hash(new_password)

	# Инвалидация всех токенов (п. 38 ТЗ)
	from secrets import token_urlsafe
	user.active_session_token = token_urlsafe(64)

	user.updated_at = datetime.utcnow()
	await session.commit()

	return True