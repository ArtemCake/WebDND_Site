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