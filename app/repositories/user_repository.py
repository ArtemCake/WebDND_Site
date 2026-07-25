# app/repositories/user_repository.py

from Config.imports import (AsyncSession, select, HTTPException)
from app.database._models import User
from app.core.security import verify_password
from app.enums.user_enums import Role_enums


# --- 1. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ ---
async def create_user(db: AsyncSession, username: str, hashed_password: str, role: str, gdpr_consent: bool) -> User:
    """
    Создает нового пользователя в БД.
    """
    try:
        user_role = Role_enums(role)
    except ValueError:
        # Если передали неверную роль, возвращаем значение по умолчанию или вызываем ошибку
        raise HTTPException(status_code=400, detail=f"Недопустимая роль: {role}")

    db_user = User(username=username, hashed_password=hashed_password, role=user_role, gdpr_consent=gdpr_consent)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user) # Обновляем объект, чтобы получить ID
    return db_user

# --- 2. ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО ИМЕНИ ---
async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """
    Возвращает объект User по username или None, если не найден.
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

# --- 3. ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО ID ---
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """
    Возвращает объект User по ID или None.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

# --- 4. ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ С ПРОВЕРКОЙ ПАРОЛЯ ---
async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """
    Находит пользователя по username и проверяет пароль.
    Возвращает объект User, если данные верны, иначе None.
    """
    # Используем уже написанную функцию для получения пользователя
    user = await get_user_by_username(db, username)

    # Проверка пароля происходит здесь, так как у нас есть объект User
    if user and verify_password(password, user.hashed_password):
        return user
    return None

async def delete_user(db: AsyncSession, user: User):
    await db.delete(user)
    await db.commit()
    return None