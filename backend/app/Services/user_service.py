# backend/app/Services/user_service.py

from Config.Config import settings
from backend.app.Services.security_service import oauth2_scheme
from backend.app.database.models.core.user import User
from Config.imports import (Optional, AsyncSession, select, PasswordHasher, update, datetime,
                            Dict, Any, UploadFile, Depends, HTTPException, status,
                            jwt, JWTError, ValidationError)
from backend.app.database.database import get_async_session


ph = PasswordHasher()

async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
	result = await session.execute(select(User).where(User.email == email))
	return result.scalar_one_or_none()

async def create_user(session: AsyncSession, nickname: str, email: str, password: str) -> User:
	hashed_pw = ph.hash(password)
	user = User(
		email=email,
		nickname=nickname,
		password_hash=hashed_pw,
		is_email_verified=False # По ТЗ подтверждение обязательно
	)
	session.add(user)
	await session.commit()
	await session.refresh(user)
	return user

async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
	user = await get_user_by_email(session, email)
	if not user:
		return None
	phr = PasswordHasher()
	try:
		phr.verify(user.password_hash, password)
		return user
	except Exception:
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
	"""
	Мягко помечает аккаунт как удаленный.
	Данные физически остаются в БД для возможности восстановления в течение 30 дней,
	согласно Политике Конфиденциальности (п. 7.3 ТЗ).
	"""
	# Проверяем, существует ли пользователь и не удален ли он уже
	result = await session.execute(select(User).where(User.id == user_id))
	user = result.scalar_one_or_none()

	if not user or user.is_active is False:
		return False

	# Помечаем как неактивного и устанавливаем дату удаления
	stmt = (
		update(User)
		.where(User.id == user_id)
		.values(
			is_active=False,
			updated_at=datetime.utcnow(),
			# Можно добавить поле deleted_at в модель User, если его еще нет
		)
	)
	await session.execute(stmt)
	await session.commit()
	return True

async def hard_delete_user(session: AsyncSession, user_id: str) -> None:
	"""
	Физическое удаление из базы. Вызывается через 30 дней после soft_delete
	фоновым таском Celery/cron или вручную администратором.
	"""
	result = await session.execute(select(User).where(User.id == user_id))
	user = result.scalar_one_or_none()
	if user:
		await session.delete(user)
		await session.commit()

async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
	"""
	Вспомогательная функция поиска пользователя по UUID.
	"""
	result = await session.execute(select(User).where(User.id == user_id))
	return result.scalar_one_or_none()

async def get_current_user(
		token: str = Depends(oauth2_scheme),
		session: AsyncSession = Depends(get_async_session)
) -> User:
	"""
	Зависимость FastAPI для получения текущего авторизованного пользователя.

	Эта функция будет автоматически вызываться везде, где стоит Depends(get_current_user).
	Она проверяет подпись токена, срок действия и наличие пользователя в БД.
	"""
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)

	try:
		# Расшифровываем payload токена. Алгоритм должен совпадать с тем, что используется при создании.
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

		# Извлекаем ID пользователя (sub - subject)
		user_id: str = payload.get("sub")
		if user_id is None:
			raise credentials_exception

		# Проверяем срок действия (exp)
		exp_timestamp = payload.get("exp")
		if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
			raise credentials_exception

	except (JWTError, ValidationError):
		raise credentials_exception

	# Ищем пользователя в базе данных
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
	"""
	Обновляет профиль пользователя: никнейм, почту и аватар.

	Args:
		target_user: Объект текущего авторизованного пользователя.
		data: Словарь с новыми данными {'nickname': ..., 'email': ...}.
		avatar_file: Файл изображения или None.

	Returns:
		Обновленный объект User.

	Raises:
		ValueError: Если новый email занят другим пользователем.
	"""
	needs_commit = False

	# 1. Обработка текстовых полей
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
		target_user.is_email_verified = False # Требуем перепроверку смены почты
		needs_commit = True

	# 2. Обработка аватара (заглушка логики сохранения)
	# В production здесь будет вызов S3/Azure Blob Storage
	if avatar_file:
		# TODO: Реализовать сохранение файла и генерацию пути
		# Для примера просто запишем заглушку в модель
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
	Меняет пароль пользователя.

	Согласно ТЗ (п. 38), при смене пароля ВСЕ активные токены должны стать невалидными.
	Это достигается путем обновления поля active_session_token у пользователя.
	"""
	phr = PasswordHasher()
	try:
		phr.verify(user.password_hash, old_password)
	except Exception:
		return False

	# 1. Обновляем хеш пароля
	user.password_hash = phr.hash(new_password)

	# 2. Инвалидация всех сессий (Требование ТЗ)
	from secrets import token_urlsafe
	user.active_session_token = token_urlsafe(64)

	user.updated_at = datetime.utcnow()
	await session.commit()

	return True