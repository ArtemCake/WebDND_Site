# web/services/user_service.py

from Config.imports import (IntegrityError, HTTPException, AsyncSession)
from app.repositories.user_repository import create_user as create_user_db, get_user_by_username, authenticate_user, delete_user
from app.core.security import get_password_hash


class UserService:
    @staticmethod
    async def register_new_user(db, username: str, password: str, role: str = "player", gdpr_consent: bool=False):
        """
        Бизнес-логика регистрации.
        Проверяет уникальность и хеширует пароль.
        """
        # Проверка на уникальность (можно было бы сделать в репозитории, но это бизнес-правило)
        existing_user = await get_user_by_username(db, username)
        if existing_user:
            return False, "Имя пользователя уже занято."

        hashed_password = get_password_hash(password)

        try:
            await create_user_db(db, username, hashed_password, role, gdpr_consent)
            return True, "Пользователь успешно создан."
        except IntegrityError as error:
            # На случай, если проверка на уникальность в БД не сработала
            return False, f"Ошибка при создании пользователя: {error}"

    @staticmethod
    async def web_login(db: AsyncSession, username: str, password: str):
        """
        Логика входа для веб-формы.
        Устанавливает куки и возвращает RedirectResponse.
        """
        try:
            user = await authenticate_user(db, username, password)
            if user is not None:
                return True, "", user
            else:
                return False, "Ошибка при авторизации пользователя. Неверное имя пользователя или пароль.", None
        except IntegrityError as e:
            # На случай, если проверка на уникальность в БД не сработала
            return False, "Ошибка при авторизации пользователя. Непредвиденная ошибка при попытке авторизации", None

    @staticmethod
    async def web_delete_user(db: AsyncSession, user):
        """
        Безопасно удаляет пользователя, используя уже существующий объект.
        """
        try:
            await delete_user(db, user)
            return True, "Аккаунт успешно удален"
        except Exception as error:
            return False, f"Ошибка при удалении пользователя: {error}"


