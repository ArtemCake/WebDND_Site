# web/core/security.py

from Config.imports import (CryptContext, timedelta, URLSafeTimedSerializer, datetime, jwt, JWTError)
from Config.Config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Создает хеш из пароля для сохранения в базу.
    Обрезает пароль до 72 БАЙТ (а не символов!) для совместимости с bcrypt.
    """
    # 1. Кодируем строку в байты (используем utf-8)
    password_bytes = password.encode('utf-8')

    # 2. Обрезаем до 72 байт
    truncated_bytes = password_bytes[:72]

    # 3. Декодируем обратно в строку.
    # 'ignore' нужен на случай, если обрезка пришлась на середину многобайтового символа.
    truncated_password = truncated_bytes.decode('utf-8', 'ignore')

    # 4. Хешируем и возвращаем результат
    return pwd_context.hash(truncated_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, совпадает ли введенный пароль с хешем из базы."""
    return pwd_context.verify(plain_password, hashed_password)

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