# app/enums/log_enums.py

from Config.imports import enum

class LogAction(enum.Enum):
	"""
	Перечисление всех возможных действий для логирования.
	Использование str, enum.Enum позволяет хранить значения в БД как строки.
	"""

	ACTION_NONE = ""

	DATABASE_MIGRATION = "Миграция базы данных"

	# Аутентификация и Регистрация
	LOGIN_SUCCESS = "Вход успешен"
	REGISTER_SUCCESS = "Регистрация успешна"
	LOGOUT = "Выход"

	# Системные события
	LOGS_CLEAR = "Очистка логов"

	# Ошибки
	DB_ERROR = "Ошибки с БД"
	LOGS_CLEAR_ERROR = "Ошибка очистки логов"
	LOGIN_FAILED = "Ошибка входа"
	USER_DELETE_FAILED = "Ошибка удаления пользователя"
	REGISTER_FAILED = "Ошибка регистрации"
	PAGE_RENDER_ERROR = "ошибка рендеринга страницы"
	LOGS_SAVE_ERROR = "Ошибка сохранения логов"
	DATABASE_ERROR = "Ошибка миграции"

	ITEM_BD_CREATED = "Создание элемента БД"
	ITEM_BD_UPDATED = "Создание элемента БД"
	ITEM_BD_DELETED = "Создание элемента БД"

	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value

class LogLevelEnum(enum.Enum):
	INFO = "info"
	WARNING = "warning"
	ERROR = "error"
	CRITICAL = "critical"
	DEBUG = "debug"
	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value