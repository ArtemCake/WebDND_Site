# app/database/database.py

from Config.imports import (
	create_async_engine, async_sessionmaker, AsyncSession, declarative_base
)
from Config.Config import settings # Берем URL из настроек

ASYNC_SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Создаем движок
engine = create_async_engine(
	ASYNC_SQLALCHEMY_DATABASE_URL,
	echo=True, # Показывает SQL запросы в консоли (удобно для отладки)
	pool_size=10,
	max_overflow=20
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
	future=True
)

# Базовый класс для моделей
Base = declarative_base()
metadata = Base.metadata