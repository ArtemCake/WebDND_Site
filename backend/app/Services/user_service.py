# backend/app/Services/user_service.py

from Config.Config import settings
from backend.app.database.models.core.user import User
from Config.imports import (Optional, AsyncSession, select, PasswordHasher, update, datetime)


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