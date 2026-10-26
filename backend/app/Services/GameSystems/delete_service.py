# backend/app/Services/GameSystems/delete_service.py

from Config.imports import (AsyncSession, delete, select, and_, column, table, text, HTTPException, UUID, DBAPIError)
from backend.app.Database.Models.Content.game_systems import (GameSystem, GameSystemRulesDraft)


_SYSTEMS = GameSystem.__table__
_DRAFTS = GameSystemRulesDraft.__table__

# Читаем реальные внешние ключи, направленные на game_systems.
# Для составного ключа сохраняем соответствие колонок и их порядок.
_INCOMING_KEYS = text("""
    SELECT
        source_ns.nspname AS source_schema,
        source.relname AS source_table,
        target_ns.nspname AS target_schema,
        array_agg(
            source_column.attname ORDER BY keys.position
        ) AS source_columns,
        array_agg(
            target_column.attname ORDER BY keys.position
        ) AS target_columns
    FROM pg_constraint AS constraint_row
    JOIN pg_class AS source
        ON source.oid = constraint_row.conrelid
    JOIN pg_namespace AS source_ns
        ON source_ns.oid = source.relnamespace
    JOIN pg_class AS target
        ON target.oid = constraint_row.confrelid
    JOIN pg_namespace AS target_ns
        ON target_ns.oid = target.relnamespace
    JOIN LATERAL unnest(
        constraint_row.conkey,
        constraint_row.confkey
    ) WITH ORDINALITY AS keys(
        source_number,
        target_number,
        position
    ) ON TRUE
    JOIN pg_attribute AS source_column
        ON source_column.attrelid = source.oid
        AND source_column.attnum = keys.source_number
    JOIN pg_attribute AS target_column
        ON target_column.attrelid = target.oid
        AND target_column.attnum = keys.target_number
    WHERE constraint_row.contype = 'f'
        AND constraint_row.confrelid = CAST(:target AS regclass)
    GROUP BY
        constraint_row.oid,
        source_ns.nspname,
        source.relname,
        target_ns.nspname
    ORDER BY source_ns.nspname, source.relname
""")

async def _assert_no_external_references(session: AsyncSession, system) -> None:
	bind = session.get_bind()
	target = bind.dialect.identifier_preparer.format_table(_SYSTEMS)

	result = await session.execute(
		_INCOMING_KEYS,
		{"target": target},
	)

	for reference in result.mappings().all():
		source_columns = list(reference["source_columns"])
		target_columns = list(reference["target_columns"])

		draft_schema = _DRAFTS.schema or reference["target_schema"]

		# Единственная разрешённая зависимость — черновик правил.
		is_draft = (
				reference["source_schema"] == draft_schema
				and reference["source_table"] == _DRAFTS.name
				and source_columns == ["system_id"]
				and target_columns == ["id"]
		)

		if is_draft:
			continue

		source = table(
			reference["source_table"],
			*[
				column(local_name, _SYSTEMS.c[target_name].type)
				for local_name, target_name in zip(
					source_columns,
					target_columns,
				)
			],
			schema=reference["source_schema"],
		)

		conditions = [
			source.c[local_name] == system[target_name]
			for local_name, target_name in zip(
				source_columns,
				target_columns,
			)
		]

		used = await session.execute(
			select(1)
			.select_from(source)
			.where(and_(*conditions))
			.limit(1)
		)

		if used.first() is not None:
			raise HTTPException(
				status_code=409,
				detail=(
					"Удаление запрещено: у системы есть игры, "
					"опубликованные версии правил или связанный контент. "
					"Деактивируйте систему, чтобы сохранить эти данные."
				),
			)

async def delete_game_system(session: AsyncSession, system_id: UUID) -> dict:
	"""Удалить свободную систему и черновик одной транзакцией.

	Сессия должна принадлежать запросу и не содержать
	посторонних несохранённых изменений.
	"""
	try:
		# Последующие проверки должны видеть изменения,
		# зафиксированные до получения блокировки системы.
		isolation = await session.execute(
			text("SHOW transaction_isolation")
		)

		if isolation.scalar_one().lower() != "read committed":
			raise HTTPException(
				status_code=503,
				detail=(
					"Удаление недоступно при текущих настройках "
					"транзакции. Обратитесь к администратору."
				),
			)

		result = await session.execute(
			select(_SYSTEMS)
			.where(_SYSTEMS.c.id == system_id)
			.with_for_update()
		)
		system = result.mappings().one_or_none()

		if system is None:
			raise HTTPException(
				status_code=404,
				detail="Игровая система не найдена.",
			)

		await _assert_no_external_references(session, system)

		# Удаляем черновик явно, затем саму систему.
		# ORM-каскады GameSystem здесь не запускаются.
		await session.execute(
			delete(_DRAFTS).where(
				_DRAFTS.c.system_id == system_id
			)
		)
		await session.execute(
			delete(_SYSTEMS).where(
				_SYSTEMS.c.id == system_id
			)
		)

		response = {
			"deleted": True,
			"system_id": str(system_id),
		}

		await session.commit()
		return response

	except DBAPIError as exc:
		await session.rollback()

		sqlstate = (
				getattr(exc.orig, "sqlstate", None)
				or getattr(exc.orig, "pgcode", None)
		)

		if sqlstate in {"23503", "40001", "40P01"}:
			raise HTTPException(
				status_code=409,
				detail=(
					"Удаление отменено из-за связанных данных "
					"или конкурентного изменения. Обновите страницу "
					"и проверьте состояние системы."
				),
			) from exc

		raise

	except Exception:
		await session.rollback()
		raise