# backend/app/Core/crypto.py

from Config.imports import (Fernet, hashlib, hmac)
from Config.Config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_value(value: str) -> str:
	return _fernet.encrypt(value.encode()).decode()

def decrypt_value(token: str) -> str:
	return _fernet.decrypt(token.encode()).decode()

def hash_email(email: str) -> str:
	normalized = email.strip().lower()
	return hmac.new(
		settings.EMAIL_HASH_KEY.encode(),
		normalized.encode(),
		hashlib.sha256
	).hexdigest()
