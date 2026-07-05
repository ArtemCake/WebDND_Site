# web/core/security.py

from Config.imports import (CryptContext, timedelta, URLSafeTimedSerializer, datetime, jwt, JWTError, PasswordHasher)
from Config.Config import settings


pwd_context = PasswordHasher()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password) # Лимитов нет!

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(hashed_password, plain_password)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Создает JWT-токен.
    data - словарь с данными (например, {"sub": user_id})
    """
    to_encode = data.copy()

    # Определяем срок действия токена
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Кодируем токен с нашим SECRET_KEY и алгоритмом из конфига
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    """
    Пробует декодировать токен.
    Возвращает payload или None, если токен невалиден.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None

serializer = URLSafeTimedSerializer(settings.SECRET_KEY)