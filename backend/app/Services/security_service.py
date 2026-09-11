# backend/app/Services/security_service.py

from Config.Config import settings
from Config.imports import (OAuth2PasswordBearer, secrets, jwt, JWTError, datetime, timedelta)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_verification_token(user_id: str, expires_delta: timedelta = None) -> str:
	"""Токен для подтверждения почты (не дает доступа к API)."""
	to_encode = {"sub": str(user_id), "purpose": "email_verification"}
	if expires_delta is None:
		expires_delta = timedelta(hours=24)
	expire = datetime.utcnow() + expires_delta
	to_encode["exp"] = expire  # <-- добавляем exp в payload, а не в encode()
	encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
	return encoded_jwt

def verify_token(token: str, purpose: str = "email_verification"):
	try:
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
		if payload.get("purpose") != purpose:
			raise JWTError("Invalid token purpose")
		return payload
	except JWTError:
		return None

async def create_jwt_pair(user_id: str, expires_delta: timedelta = None):
	"""Генерация пары Access и Refresh токенов."""
	if expires_delta is None:
		expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	expire = datetime.utcnow() + expires_delta

	access_data = {"sub": str(user_id), "type": "access", "exp": expire}
	refresh_expire = datetime.utcnow() + timedelta(days=7)
	refresh_data = {"sub": str(user_id), "type": "refresh", "exp": refresh_expire}

	return {
		"access_token": jwt.encode(access_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
		"refresh_token": jwt.encode(refresh_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
	}

async def blacklist_token(token: str):
	"""Заглушка. В production здесь будет запись в Redis SET с TTL остатка жизни токена."""
	pass