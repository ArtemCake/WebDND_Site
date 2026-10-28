# backend/db_migrations/rule_engine_protection.py

"""Автоматическое добавление защиты публикаций в миграции Alembic."""

from alembic.operations import ops
from sqlalchemy import text


TABLE_NAME = "rule_engine_versions"
TRIGGER_NAME = "trg_rule_engine_versions_immutable"
FUNCTION_NAME = "worldloom_guard_rule_engine_version"


CREATE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION worldloom_guard_rule_engine_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Published rule engine versions are immutable'
        USING ERRCODE = '23514';
    RETURN NULL;
END;
$$;
"""

CREATE_TRIGGER_SQL = """
CREATE TRIGGER trg_rule_engine_versions_immutable
BEFORE UPDATE OR DELETE ON rule_engine_versions
FOR EACH ROW
EXECUTE FUNCTION worldloom_guard_rule_engine_version();
"""

DROP_TRIGGER_SQL = """
DROP TRIGGER trg_rule_engine_versions_immutable
ON rule_engine_versions;
"""

DROP_FUNCTION_SQL = """
DROP FUNCTION worldloom_guard_rule_engine_version();
"""


FIND_TRIGGER_SQL = text("""
    SELECT
        t.tgenabled AS enabled_mode,
        t.tgtype AS trigger_type,
        p.proname AS function_name,
        p.pronargs AS function_arguments,
        pn.nspname = tn.nspname AS same_schema
    FROM pg_trigger AS t
    JOIN pg_class AS c
        ON c.oid = t.tgrelid
    JOIN pg_namespace AS tn
        ON tn.oid = c.relnamespace
    JOIN pg_proc AS p
        ON p.oid = t.tgfoid
    JOIN pg_namespace AS pn
        ON pn.oid = p.pronamespace
    WHERE t.tgrelid = to_regclass(:table_name)
      AND t.tgname = :trigger_name
      AND NOT t.tgisinternal
""")


def add_rule_engine_protection(
		migration_context,
		revision,
		directives,
):
	"""
	Дополнить создаваемую миграцию, если защиты ещё нет.

	Подключается через process_revision_directives в env.py.
	Не выполняет DDL при генерации: только добавляет операции
	в будущий файл миграции.
	"""
	if not directives:
		return

	metadata = migration_context.opts.get("target_metadata")

	if metadata is None or TABLE_NAME not in metadata.tables:
		return

	connection = migration_context.connection

	if connection is None:
		raise RuntimeError(
			"Для проверки защиты публикаций нужно подключение к БД."
		)

	if connection.dialect.name != "postgresql":
		raise RuntimeError(
			"Защита публикаций рассчитана на PostgreSQL."
		)

	trigger = connection.execute(
		FIND_TRIGGER_SQL,
		{
			"table_name": TABLE_NAME,
			"trigger_name": TRIGGER_NAME,
		},
	).mappings().one_or_none()

	if trigger is not None:
		# PostgreSQL tgtype:
		# ROW (1) + BEFORE (2) + DELETE (8) + UPDATE (16) = 27.
		expected_trigger = (
				trigger["enabled_mode"] in {"O", "A"}
				and trigger["trigger_type"] == 27
				and trigger["function_name"] == FUNCTION_NAME
				and trigger["function_arguments"] == 0
				and trigger["same_schema"]
		)

		if not expected_trigger:
			raise RuntimeError(
				"Триггер защиты публикаций уже существует, "
				"но отключён или имеет неожиданную конфигурацию. "
				"Нужна отдельная проверка перед генерацией миграции."
			)

		return

	if len(directives) != 1:
		raise RuntimeError(
			"Автогенерация защиты ожидает один файл миграции."
		)

	script = directives[0]

	if (
			len(script.upgrade_ops_list) != 1
			or len(script.downgrade_ops_list) != 1
	):
		raise RuntimeError(
			"Автогенерация защиты ожидает одну БД."
		)

	upgrade_operations = script.upgrade_ops_list[0].ops
	downgrade_operations = script.downgrade_ops_list[0].ops

	# В начальной миграции таблица должна быть создана раньше триггера.
	upgrade_operations.extend([
		ops.ExecuteSQLOp(CREATE_FUNCTION_SQL),
		ops.ExecuteSQLOp(CREATE_TRIGGER_SQL),
	])

	# При откате сначала снимаем защиту, затем удаляем таблицу,
	# если её удаление присутствует в этой миграции.
	downgrade_operations[0:0] = [
		ops.ExecuteSQLOp(DROP_TRIGGER_SQL),
		ops.ExecuteSQLOp(DROP_FUNCTION_SQL),
	]
