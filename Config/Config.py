# Config/web_config.py

from web.imports.imports import (BaseSettings, SettingsConfigDict, os)


# --- НАСТРОЙКИ ТАЙМЕРА ---
TIMER_DEFAULT_INTERVAL_MIN: int = 5  # Минуты


class WebAppSettings(BaseSettings):
	"""
	Конфигурационные параметры для веб-приложения.
	Значения по умолчанию можно переопределить через переменные окружения или .env файл.
	"""

	# --- Основные настройки API ---
	API_V1_STR: str = "/api/v1"
	PROJECT_NAME: str = "StreamAlertBot API"
	DESCRIPTION: str = "Веб-API для управления уведомлениями о трансляциях Twitch"
	VERSION: str = "1.0.0"

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

	# --- Настройки Telegram API ---
	TELEGRAM_BOT_TOKEN: str  # ОБЯЗАТЕЛЬНО указать в .env файле
	TELEGRAM_API_ID: str     # ОБЯЗАТЕЛЬНО указать в .env файле
	TELEGRAM_API_HASH: str   # ОБЯЗАТЕЛЬНО указать в .env файле

	ADMIN_PASSWORD: str   # ОБЯЗАТЕЛЬНО указать в .env файле

	# --- Настройки Twitch API ---

	# --- Настройки Twitch API ---
	TWITCH_CLIENT_ID: str  # ОБЯЗАТЕЛЬНО указать в .env файле
	TWITCH_CLIENT_SECRET: str  # ОБЯЗАТЕЛЬНО указать в .env файле

	# --- Глобальные пути проекта (добавлены для удобства) ---
	TIMER_DEFAULT_INTERVAL_MIN: int = TIMER_DEFAULT_INTERVAL_MIN

	# --- Настройки CORS (для фронтенда) ---
	@property
	def BACKEND_CORS_ORIGINS(self) -> list[str]:
		"""Возвращает список разрешенных origin для CORS."""
		return [item.strip() for item in os.environ.get("BACKEND_CORS_ORIGINS", "").split(',')]

	model_config = SettingsConfigDict(
		env_file="/data/.env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",  # Игнорирует лишние переменные в .env
	)

# Создаем глобальный объект настроек, который можно импортировать в других файлах
settings = WebAppSettings()