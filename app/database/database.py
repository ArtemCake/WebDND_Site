# app/database/database.py

from Config.imports import (create_async_engine, sessionmaker, AsyncSession, MetaData, declarative_base)


# --- НАСТРОЙКИ ---
# Обычно DATABASE_URL хранится в .env файле или Config.py
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
# Для локальной разработки можно использовать SQLite:
# DATABASE_URL = "sqlite+aiosqlite:///./db.sqlite"

# --- СОЗДАНИЕ ОБЪЕКТОВ БД ---
# Создаем движок (engine), который будет управлять соединениями
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаем фабрику сессий. Она будет создавать новые сессии для каждого запроса.
AsyncSessionLocal = sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
)

# --- МЕТАДАННЫЕ И БАЗОВЫЙ КЛАСС ---
# Создаем единый объект metadata, который соберет информацию обо ВСЕХ моделях.
metadata = MetaData()

# Создаем Базовый класс (Base). Все наши модели будут наследоваться от него.
# Важно передать ему наш общий объект metadata!
Base = declarative_base(metadata=metadata)