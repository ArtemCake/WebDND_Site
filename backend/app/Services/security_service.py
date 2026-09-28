# backend/app/Services/security_service.py

from Config.Config import settings
from Config.imports import (OAuth2PasswordBearer, jwt, JWTError, datetime, timedelta)
from backend.app.database.models.core.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def create_verification_token(user_id: str, expires_delta: timedelta = None) -> str:
	"""Токен для подтверждения почты (не дает доступа к API)."""
	to_encode = {"sub": str(user_id), "purpose": "email_verification"}
	if expires_delta is None:
		expires_delta = timedelta(hours=24)
	expire = datetime.utcnow() + expires_delta
	to_encode["exp"] = expire
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

async def create_jwt_pair(user_obj_or_id, expires_delta: timedelta = None, session_token: str | None = None):
	"""
	Генерация пары Access и Refresh токенов.
	Принимает либо ID строкой, либо объект User.

	ФИКС: session_token встраивается в claim "sid" — это позволяет
	get_current_user сверять токен с active_session_token в базе и
	реально завершать сессии при логауте/смене пароля/удалении аккаунта,
	а не только менять значение в БД, которое никто не проверяет.
	"""
	user_id_str = ""

	if hasattr(user_obj_or_id, 'id'):
		if not hasattr(user_obj_or_id, 'is_active') or not hasattr(user_obj_or_id, 'is_email_verified'):
			raise PermissionError("User object missing security flags.")

		if not user_obj_or_id.is_active:
			raise PermissionError("Cannot generate tokens for inactive user.")
		if not user_obj_or_id.is_email_verified:
			raise PermissionError("Cannot generate tokens for unverified user.")

		user_id_str = str(user_obj_or_id.id)
	else:
		user_id_str = str(user_obj_or_id)

	if expires_delta is None:
		expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	expire = datetime.utcnow() + expires_delta

	access_data = {"sub": user_id_str, "type": "access", "exp": expire, "sid": session_token}
	refresh_expire = datetime.utcnow() + timedelta(days=7)
	refresh_data = {"sub": user_id_str, "type": "refresh", "exp": refresh_expire, "sid": session_token}

	return {
		"access_token": jwt.encode(access_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
		"refresh_token": jwt.encode(refresh_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
	}