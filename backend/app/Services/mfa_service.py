# backend/app/Services/mfa_service.py

"""
Двухфакторная аутентификация (TOTP) и резервные коды восстановления.
Секрет в MFADevice.secret хранится зашифрованным (Fernet, ключ из SECRET_KEY) —
без новой миграции и без отдельного секрета шифрования.
Резервные коды — отдельные записи MFADevice(type="backup_code"), secret — их
Argon2id-хеш через тот же pwd_context, что и у паролей пользователей.
"""

from Config.imports import (AsyncSession, select, delete, Fernet, InvalidToken, pyotp, secrets,
                            hashlib, base64)
from Config.Config import settings
from backend.app.Database.Models.Core.user import User, MFADevice
from backend.app.Services.user_service import pwd_context


TOTP_DEVICE_TYPE = "totp"
BACKUP_CODE_TYPE = "backup_code"
BACKUP_CODES_COUNT = 8

def _get_fernet() -> Fernet:
	key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
	return Fernet(base64.urlsafe_b64encode(key))

def _encrypt(value: str) -> str:
	return _get_fernet().encrypt(value.encode()).decode()

def _decrypt(token: str) -> str:
	return _get_fernet().decrypt(token.encode()).decode()

async def get_totp_device(session: AsyncSession, user_id) -> MFADevice | None:
	result = await session.execute(
		select(MFADevice).where(MFADevice.user_id == user_id, MFADevice.type == TOTP_DEVICE_TYPE)
	)
	return result.scalar_one_or_none()

async def start_totp_setup(session: AsyncSession, user: User) -> tuple[str, str]:
	"""
	Создаёт новое TOTP-устройство (ещё не подтверждённое). Отдельного флага
	"confirmed" в модели нет — пока user.is_2fa_enabled == False, устройство
	считается черновиком и свободно перезаписывается повторным вызовом.
	"""
	existing = await get_totp_device(session, user.id)
	if existing:
		await session.delete(existing)
		await session.flush()

	secret = pyotp.random_base32()
	device = MFADevice(
		user_id=user.id,
		type=TOTP_DEVICE_TYPE,
		secret=_encrypt(secret),
		label="Приложение-аутентификатор",
	)
	session.add(device)
	await session.commit()

	uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.PROJECT_NAME)
	return secret, uri

async def confirm_totp_setup(session: AsyncSession, user: User, code: str) -> list[str] | None:
	"""Подтверждает код от только что настроенного устройства, включает 2FA и выдаёт резервные коды (один раз)."""
	device = await get_totp_device(session, user.id)
	if not device:
		return None

	try:
		secret = _decrypt(device.secret)
	except InvalidToken:
		return None

	if not pyotp.TOTP(secret).verify(code.strip(), valid_window=1):
		return None

	user.is_2fa_enabled = True

	# Старые резервные коды (если это переустановка) больше не действительны
	await session.execute(delete(MFADevice).where(MFADevice.user_id == user.id, MFADevice.type == BACKUP_CODE_TYPE))

	backup_codes = [secrets.token_hex(4) for _ in range(BACKUP_CODES_COUNT)]
	for plain_code in backup_codes:
		session.add(MFADevice(
			user_id=user.id,
			type=BACKUP_CODE_TYPE,
			secret=pwd_context.hash(plain_code),
			is_backup=True,
		))

	await session.commit()
	return backup_codes

async def verify_login_code(session: AsyncSession, user: User, code: str) -> bool:
	"""Проверка кода на входе: сначала TOTP, при неудаче — одноразовый резервный код (сгорает после использования)."""
	code = code.strip().replace(" ", "")

	device = await get_totp_device(session, user.id)
	if device:
		try:
			if pyotp.TOTP(_decrypt(device.secret)).verify(code, valid_window=1):
				return True
		except InvalidToken:
			pass

	result = await session.execute(
		select(MFADevice).where(MFADevice.user_id == user.id, MFADevice.type == BACKUP_CODE_TYPE)
	)
	for backup in result.scalars().all():
		try:
			if pwd_context.verify(code, backup.secret):
				await session.delete(backup)
				await session.commit()
				return True
		except (ValueError, TypeError):
			continue

	return False

async def disable_mfa(session: AsyncSession, user: User) -> None:
	await session.execute(delete(MFADevice).where(MFADevice.user_id == user.id))
	user.is_2fa_enabled = False
	await session.commit()