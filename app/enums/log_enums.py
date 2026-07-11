# web/enums/log_actions.py

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

	# Действия с данными (CRUD)
	PRESET_CREATED = "Создание пресета"
	PRESET_UPDATED = "Обновление пресета"
	PRESET_DELETED = "Удаление пресета"

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