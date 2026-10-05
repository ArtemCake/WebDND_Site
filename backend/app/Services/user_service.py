# backend/app/Services/user_service.py

from Config.Config import settings
from backend.app.database.models.core.user import User
from Config.imports import (Optional, AsyncSession, select, Depends, HTTPException, status,
                            jwt, JWTError, datetime, ValidationError, Dict, Any, UploadFile, update, CryptContext,
                            Request)
from backend.app.database.database import get_async_session
from backend.app.enums.enums_BD import SystemRole


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
	result = await session.execute(select(User).where(User.email == email))
	return result.scalar_one_or_none()

async def create_user(
		session: AsyncSession,
		nickname: str,
		email: str,
		password: str,
		roles: list[SystemRole] | None = None
) -> User:
	hashed_pw = pwd_context.hash(password)
	user = User(
		email=email,
		nickname=nickname,
		password_hash=hashed_pw,
		is_email_verified=False,
		roles=roles or [SystemRole.PLAYER],
	)
	session.add(user)
	await session.commit()
	await session.refresh(user)
	return user

async def add_role(session: AsyncSession, user: User, role: SystemRole) -> User:
	"""Добавляет роль, не трогая остальные уже имеющиеся."""
	if role not in (user.roles or []):
		user.roles = [*(user.roles or []), role]
		await session.commit()
		await session.refresh(user)
	return user

async def remove_role(session: AsyncSession, user: User, role: SystemRole) -> User:
	"""Убирает одну роль, остальные остаются."""
	if user.roles and role in user.roles:
		user.roles = [r for r in user.roles if r != role]
		await session.commit()
		await session.refresh(user)
	return user

async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
	user = await get_user_by_email(session, email)
	if not user:
		return None

	try:
		if not pwd_context.verify(password, user.password_hash):
			return None
		return user
	except (ValueError, TypeError) as e:
		from Config.logger import setup_logging
		log = setup_logging(app_name="WebDND_Site")
		log.error(f"[AUTH][CRYPTO_ERROR] Argon2 verification failed for {email}: {str(e)}")
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

def _decode_and_extract(token: str, credentials_exception: HTTPException) -> tuple[str, str | None]:
	try:
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

		if payload.get("type") != "access":
			raise credentials_exception

		user_id: str = payload.get("sub")
		if user_id is None:
			raise credentials_exception

		exp_timestamp = payload.get("exp")
		if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
			raise credentials_exception

		return user_id, payload.get("sid")
	except (JWTError, ValidationError):
		raise credentials_exception

async def get_current_user(
		request: Request,
		session: AsyncSession = Depends(get_async_session)
) -> User:
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)

	token = None
	auth_header = request.headers.get("Authorization")
	if auth_header and auth_header.startswith("Bearer "):
		token = auth_header.split(" ")[1]

	if not token:
		token = request.cookies.get("access_token")

	if not token:
		raise credentials_exception

	user_id, sid = _decode_and_extract(token, credentials_exception)

	user = await get_user_by_id(session, user_id)
	if user is None or not user.is_active:
		raise credentials_exception

	# ФИКС: реальная инвалидация сессии. Раньше active_session_token
	# перезаписывался при логауте/смене пароля/удалении аккаунта, но
	# здесь никогда не проверялся — старый JWT продолжал работать до
	# истечения своего срока действия (до 7 дней), несмотря на "выход
	# со всех устройств". Теперь токен обязан нести тот же sid, что
	# сейчас хранится в БД у пользователя.
	if not sid or user.active_session_token != sid:
		raise credentials_exception

	return user

async def get_optional_user(
		request: Request,
		session: AsyncSession = Depends(get_async_session)
) -> User | None:
	"""То же самое, но без исключения — для страниц, где авторизация не обязательна
	(login/register должны просто понимать, что пользователь уже вошёл)."""
	try:
		return await get_current_user(request, session)
	except HTTPException:
		return None

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
		existing_nick = await session.execute(select(User).where(User.nickname == new_nickname))
		if existing_nick.scalar_one_or_none():
			raise ValueError("Nickname already exists")
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
	if not user.password_hash:
		return False

	try:
		if not pwd_context.verify(old_password, user.password_hash):
			return False
	except Exception:
		return False

	user.password_hash = pwd_context.hash(new_password)

	from secrets import token_urlsafe
	user.active_session_token = token_urlsafe(64)

	user.updated_at = datetime.utcnow()
	await session.commit()

	return True