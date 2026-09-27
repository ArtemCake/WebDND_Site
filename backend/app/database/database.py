# backend/app/database/database.py

"""
Модуль управления подключениями к базе данных PostgreSQL.
Использует SQLAlchemy 2.x AsyncIO согласно списку библиотек в ТЗ.
"""

from Config.imports import (create_async_engine, async_sessionmaker, AsyncSession,
	declarative_base)
from Config.Config import settings
from Config.logger import setup_logging


ASYNC_SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
log = setup_logging(app_name="WebDND_Site")
# --- ПАРАМЕТРЫ ПУЛА ПОДКЛЮЧЕНИЙ (вынесены из магических чисел) ---
POOL_SIZE = 10
MAX_OVERFLOW = 20

def get_engine_echo_mode() -> bool:
	"""
	Определяет режим вывода SQL-запросов в консоль.
	Включается только в среде разработки для отладки.
	"""
	return settings.ENVIRONMENT == "development"

try:
	# Создаем единый асинхронный движок (Исправление DUP-001: удален дубль engine_logs)
	engine = create_async_engine(
		ASYNC_SQLALCHEMY_DATABASE_URL,
		echo=get_engine_echo_mode(),
		pool_size=POOL_SIZE,
		max_overflow=MAX_OVERFLOW,
		pool_pre_ping=True  # Проверка жизнеспособности соединения перед использованием
	)
except Exception as e:
	# Логируем фатальную ошибку инициализации БД (FIX FOR LOG-004)
	log.critical(f"[DB] Failed to initialize database engine: {e}")
	raise

# Фабрика сессий для основного приложения (игровые данные, пользователи)
AsyncSessionLocal = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
	future=True
)

# Базовый класс для всех моделей БД
Base = declarative_base()
metadata = Base.metadata

async def get_async_session() -> AsyncSession:
	"""
	FastAPI Dependency для получения сессии базы данных.

	Yields:
		AsyncSession: Асинхронная сессия SQLAlchemy.

	Автоматически закрывает сессию после завершения запроса благодаря контекстному менеджеру.
	"""
	try:
		async with AsyncSessionLocal() as session:
			yield session
	except Exception as db_error:
		# Логируем ошибки работы с сессией (FIX FOR LOG-004)
		log.error(f"[DB][SESSION] Session error: {db_error}")
		raise
