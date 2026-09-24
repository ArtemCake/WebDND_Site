# Config/Config.py

from Config.imports import (BaseSettings, SettingsConfigDict, os, Path)


# --- НАСТРОЙКИ ТАЙМЕРА ---
TIMER_DEFAULT_INTERVAL_MIN: int = 5  # Минуты


class WebAppSettings(BaseSettings):
	"""
	Конфигурационные параметры для веб-приложения.
	Значения по умолчанию можно переопределить через переменные окружения или .env файл.
	"""

	# --- НАСТРОЙКИ ПОЧТОВОГО СЕРВЕРА ---
	SMTP_HOST: str          # ОБЯЗАТЕЛЬНО указать в .env файле
	SMTP_PORT: int          # 465 для SSL, 587 для STARTTLS
	SMTP_USE_TLS: bool      # false для порта 465 (SSL), true для порта 587
	SMTP_USE_SSL: bool      # true для порта 465, false для порта 587

	SMTP_USER: str          # Логин почтового ящика
	SMTP_PASSWORD: str      # Пароль приложения (ВАЖНО: не основной пароль от почты)

	MAIL_SENDER_NAME: str
	MAIL_SENDER_EMAIL: str
	MAIL_SUPPORT_EMAIL: str

	# --- Основные настройки API ---
	API_V1_STR: str = "/api/v1"
	PROJECT_NAME: str = "WebDND_Site API"
	DESCRIPTION: str = "Веб-API для управления сайтом по ДНД"
	VERSION: str = "1.0.0"

	_base_dir: Path = Path(__file__).resolve().parent.parent

	@property
	def BASE_DIR(self) -> str:
		return self._base_dir.as_posix()

	# НОВЫЕ НАСТРОЙКИ ДЛЯ POSTGRESQL
	POSTGRES_USER: str  # Логин
	POSTGRES_PASSWORD: str  # Пароль
	POSTGRES_DB: str  # Имя базы данных
	POSTGRES_HOST: str  # Адрес сервера
	POSTGRES_PORT: str  # Порт

	ASYNC_DB_DRIVER: str = "postgresql+asyncpg"

	@property
	def DATABASE_URL(self) -> str:
		return f"{self.ASYNC_DB_DRIVER}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

	# --- Настройки JWT (Аутентификация) ---
	SECRET_KEY: str  # ОБЯЗАТЕЛЬНО указать в .env файле
	ALGORITHM: str = "HS256"
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
	FRONTEND_URL: str
	ADMIN_PASSWORD: str   # ОБЯЗАТЕЛЬНО указать в .env файле

	# --- Настройки Twitch API ---

	# --- Глобальные пути проекта (добавлены для удобства) ---
	TIMER_DEFAULT_INTERVAL_MIN: int = TIMER_DEFAULT_INTERVAL_MIN

	# --- Настройки CORS (для фронтенда) ---
	@property
	def BACKEND_CORS_ORIGINS(self) -> list[str]:
		raw = os.getenv("BACKEND_CORS_ORIGINS", "")
		if not raw:
			return []
		return [url.strip() for url in raw.split(",") if url.strip()]

	model_config = SettingsConfigDict(
		env_file="data/.env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",  # Игнорирует лишние переменные в .env
	)


# Глобальный объект
try:
	settings = WebAppSettings()
except Exception as e:
	print(f"[CONFIG FATAL] Cannot load settings: {e}")
	# Создаем пустой объект-заглушку, чтобы main.py не упал при импорте
	class DummySettings:
		pass
	settings = DummySettings()