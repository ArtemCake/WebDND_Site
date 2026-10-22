# backend/app/Services/Core/security_service.py

from Config.Config import settings
from Config.imports import (OAuth2PasswordBearer, jwt, JWTError, datetime, timedelta, hashlib,
                            update, secrets, AsyncSession, JSONResponse, Response)
from backend.app.Database.Models.Core.user import User
from Config.logger import setup_logging


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
log = setup_logging(app_name="WorldLoom")

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

async def issue_login_session(user: User, session: AsyncSession) -> JSONResponse:
	"""Общий хвост успешного входа: пара JWT, cookie, обновление active_session_token."""
	new_session_token = secrets.token_urlsafe(64)
	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	tokens = await create_jwt_pair(
		user_obj_or_id=user,
		expires_delta=access_token_expires,
		session_token=new_session_token
	)

	log.info(f"[AUTH][SUCCESS] Login session issued for {user.email} (ID: {user.id})")

	response = JSONResponse(content={
		"access_token": tokens["access_token"],
		"token_type": "bearer",
		"refresh_token": tokens["refresh_token"]
	})
	set_auth_cookie(response, "access_token", tokens["access_token"], settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
	set_auth_cookie(response, "refresh_token", tokens["refresh_token"], 7 * 24 * 60 * 60)

	stmt = (
		update(User)
		.where(User.id == user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	return response

def create_password_reset_token(user, expires_delta: timedelta = None) -> str:
	"""
	Токен для сброса пароля. Короткий срок жизни (30 минут) плюс отпечаток
	текущего password_hash в payload: как только пароль сменится — отпечаток
	перестанет совпадать и ссылка станет недействительной даже раньше exp
	(защита от повторного использования уже применённой ссылки).
	"""
	fingerprint = hashlib.sha256((user.password_hash or "").encode()).hexdigest()[:16]
	to_encode = {"sub": str(user.id), "purpose": "password_reset", "pwfp": fingerprint}
	if expires_delta is None:
		expires_delta = timedelta(minutes=30)
	expire = datetime.utcnow() + expires_delta
	to_encode["exp"] = expire
	return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_mfa_pending_token(user_id: str, expires_delta: timedelta = None) -> str:
	"""Короткоживущий токен между вводом пароля и вводом TOTP-кода — сам по себе доступа к API не даёт."""
	to_encode = {"sub": str(user_id), "purpose": "mfa_pending"}
	if expires_delta is None:
		expires_delta = timedelta(minutes=5)
	expire = datetime.utcnow() + expires_delta
	to_encode["exp"] = expire
	return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def set_auth_cookie(response: Response, key: str, value: str, max_age: int):
	response.set_cookie(
		key=key,
		value=value,
		max_age=max_age,
		httponly=True,                                      # недоступна из JS — защита от XSS-кражи токена
		secure=settings.SECURE_COOKIES,        # только по HTTPS; на локальной разработке придётся временно False
		samesite="lax",                                     # защита от CSRF при переходах с чужих сайтов; "strict" — ещё жёстче, но может мешать переходам по ссылке из письма
		path="/",
	)

def clear_auth_cookie(response: Response, key: str) -> None:
	response.delete_cookie(
		key=key,
		path="/",
		httponly=True,
		secure=settings.SECURE_COOKIES,
		samesite="lax",
	)