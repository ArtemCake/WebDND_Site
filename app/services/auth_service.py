# app/services/auth_service.py

from Config.imports import (timedelta)
from app.core.security import create_access_token
from app.repositories.user_repository import authenticate_user

class AuthService:
    @staticmethod
    async def login(db, username: str, password: str, token_expiry_minutes: int):
        """
        Бизнес-логика входа.
        Проверяет учетные данные и возвращает JWT-токен.
        """
        # 1. Проверяем логин и пароль через репозиторий
        user = await authenticate_user(db, username, password)

        if not user:
            return False, None, "Неверное имя пользователя или пароль."

        # 2. Если пользователь найден, создаем токен
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=token_expiry_minutes)
        )

        return True, access_token, "Вход выполнен успешно."


