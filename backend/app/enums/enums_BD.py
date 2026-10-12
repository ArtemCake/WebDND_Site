# backend/app/enums/enums_BD.py

from Config.imports import PG_ENUM, StrEnum


class SystemRole(StrEnum):
	PLAYER = "player"
	MASTER = "master"
	EDITOR = "editor"
	ADMIN = "admin"

	@staticmethod
	def pg_enum_type():
		# Возвращаем готовый тип.
		# *[role.value for role in SystemRole] — распаковываем список в аргументы,
		# чтобы избежать ошибки "unhashable type: 'list'" во внутренних структурах SQLAlchemy.
		return PG_ENUM(
			SystemRole,
			name="system_role_type",
			create_type=True,
			validate_strings=True,
			values_callable=lambda enum_cls: [member.value for member in enum_cls],
		)

class AdminPermission(StrEnum):
	"""
	Гранулярные права внутри роли admin. Роль ADMIN сама по себе
	даёт только вход в /admin — конкретные разделы (пользователи,
	контент, жалобы, аудит-лог, система) открываются только тем,
	кому явно выдано соответствующее право.
	"""
	USERS = "users"       # управление пользователями: роли, права, удаление
	CONTENT = "content"   # модерация справочников контента
	REPORTS = "reports"   # жалобы на контент и профили
	AUDIT = "audit"       # журнал критических действий
	SYSTEM = "system"     # системные события, настройки сервера

	@staticmethod
	def pg_enum_type():
		return PG_ENUM(
			AdminPermission,
			name="admin_permission_type",
			create_type=True,
			validate_strings=True,
			values_callable=lambda enum_cls: [member.value for member in enum_cls],
		)