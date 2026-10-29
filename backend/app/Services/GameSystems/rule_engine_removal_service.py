# backend/app/Services/GameSystems/rule_engine_removal_service.py

"""Confirmed engine removal or deactivation.

Administrative permission is checked by the HTTP dependency.
The existing owner-only engine policy is preserved.

Deletion of additional system content is deliberately rejected
until its dependencies have an explicit deletion implementation.
"""

from Config.imports import (DBAPIError, and_, column, delete, select, table, text, update, HTTPException, UUID, json, hashlib)
from backend.app.Database._models import (GameSystem, GameSystemRulesDraft, GameSystemRulesVersion, RuleEngine, RuleEngineVersion)
from backend.app.Services.Games import game_deletion_service
from backend.app.Services.GameSystems import delete_service
from backend.app.Schemas.rule_engine_removal import (RuleEngineRemovalExecute, RuleEngineRemovalPlan, RuleEngineRemovalResult)


_ENGINES = RuleEngine.__table__
_ENGINE_VERSIONS = RuleEngineVersion.__table__
_SYSTEMS = GameSystem.__table__
_SYSTEM_DRAFTS = GameSystemRulesDraft.__table__
_SYSTEM_VERSIONS = GameSystemRulesVersion.__table__


# One SQL statement: all rows belong to one statement snapshot.
#
# Include ALL rules of linked systems, not only the rules pointing
# at this engine. Whole systems are the unit of this operation.
_SNAPSHOT_SQL = text("""
    WITH selected_engine AS (
        SELECT *
        FROM rule_engines
        WHERE id = :engine_id
          AND owner_id = :actor_id
    ),
    engine_versions AS (
        SELECT v.*
        FROM rule_engine_versions AS v
        JOIN selected_engine AS e ON e.id = v.engine_id
    ),
    origin_systems AS (
        SELECT d.system_id
        FROM game_system_rules_drafts AS d
        JOIN engine_versions AS v ON v.id = d.engine_version_id

        UNION

        SELECT r.system_id
        FROM game_system_rules_versions AS r
        JOIN engine_versions AS v ON v.id = r.engine_version_id
    ),
    linked_systems AS (
        SELECT s.*
        FROM game_systems AS s
        JOIN origin_systems AS o ON o.system_id = s.id
    ),
    linked_games AS (
        SELECT g.*
        FROM games AS g
        JOIN linked_systems AS s ON s.id = g.system_id
    ),
    linked_sessions AS (
        SELECT s.*
        FROM sessions AS s
        JOIN linked_games AS g ON g.id = s.game_id
    )
    SELECT jsonb_build_object(
        'engine',
        (SELECT to_jsonb(e) FROM selected_engine AS e),

        'engine_drafts',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(d) ORDER BY d.id)
            FROM rule_engine_drafts AS d
            JOIN selected_engine AS e ON e.id = d.engine_id
        ), '[]'::jsonb),

        'engine_versions',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(v) ORDER BY v.id)
            FROM engine_versions AS v
        ), '[]'::jsonb),

        'systems',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(s) ORDER BY s.id)
            FROM linked_systems AS s
        ), '[]'::jsonb),

        'system_drafts',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(d) ORDER BY d.id)
            FROM game_system_rules_drafts AS d
            JOIN linked_systems AS s ON s.id = d.system_id
        ), '[]'::jsonb),

        'system_versions',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(v) ORDER BY v.id)
            FROM game_system_rules_versions AS v
            JOIN linked_systems AS s ON s.id = v.system_id
        ), '[]'::jsonb),

        'games',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(g) ORDER BY g.id)
            FROM linked_games AS g
        ), '[]'::jsonb),

        'sessions',
        COALESCE((
            SELECT jsonb_agg(to_jsonb(s) ORDER BY s.id)
            FROM linked_sessions AS s
        ), '[]'::jsonb)
    )
""")


# Conservative initial implementation:
# freeze writes and row-locking reads of the lifecycle tables.
# Plain SELECT remains possible.
#
# NOWAIT prevents waiting for a busy gameplay transaction.
_LOCK_SQL = text("""
    LOCK TABLE
        rule_engines,
        rule_engine_drafts,
        rule_engine_versions,
        game_systems,
        game_system_rules_drafts,
        game_system_rules_versions,
        games,
        sessions
    IN EXCLUSIVE MODE NOWAIT
""")


def _token(snapshot: dict) -> str:
	payload = json.dumps(
		snapshot,
		sort_keys=True,
		ensure_ascii=False,
		separators=(",", ":"),
	).encode("utf-8")

	return hashlib.sha256(payload).hexdigest()

def _action(snapshot: dict) -> str:
	# Current API creates a Session when it starts.
	# Ended sessions remain protective.
	if snapshot["sessions"]:
		return "deactivate"

	if any(
			game["master_id"] is None
			for game in snapshot["games"]
	):
		return "blocked"

	return "delete"

async def _read_snapshot(session, engine_id, actor_id) -> dict:
	result = await session.execute(
		_SNAPSHOT_SQL,
		{
			"engine_id": engine_id,
			"actor_id": actor_id,
		},
	)
	snapshot = result.scalar_one()

	if snapshot["engine"] is None:
		raise HTTPException(404, "Движок не найден.")

	return snapshot

def _validate_actor(actor_id):
	if not isinstance(actor_id, UUID):
		raise HTTPException(
			401,
			"Требуется авторизованный пользователь.",
		)

async def get_removal_plan(session, engine_id: UUID,actor_id: UUID) -> RuleEngineRemovalPlan:
	_validate_actor(actor_id)
	snapshot = await _read_snapshot(
		session,
		engine_id,
		actor_id,
	)

	return RuleEngineRemovalPlan(
		engine_id=engine_id,
		engine_name=snapshot["engine"]["name"],
		versions_count=len(snapshot["engine_versions"]),
		systems_count=len(snapshot["systems"]),
		games_count=len(snapshot["games"]),
		sessions_count=len(snapshot["sessions"]),
		unowned_games_count=sum(
			game["master_id"] is None
			for game in snapshot["games"]
		),
		proposed_action=_action(snapshot),
		snapshot_token=_token(snapshot),
	)

async def _lock_graph(session) -> None:
	if session.get_bind().dialect.name != "postgresql":
		raise HTTPException(
			409,
			"Операция рассчитана на PostgreSQL.",
		)

	isolation = (
		await session.execute(
			text("SHOW transaction_isolation")
		)
	).scalar_one()

	if isolation.lower() != "read committed":
		raise HTTPException(
			409,
			"Для этой операции требуется READ COMMITTED.",
		)

	# Bound waits caused by secondary FK/cascade locks.
	await session.execute(
		text("SET LOCAL lock_timeout = '3s'")
	)
	await session.execute(_LOCK_SQL)

async def _reject_extra_system_content(session, system_ids: list[UUID]) -> None:
	"""Fail closed for dependencies not handled by this executor.

	Reuse the existing catalog query, including composite keys.
	Do not assume that every dependent row has system_id.
	"""
	if not system_ids:
		return

	references = (
		await session.execute(delete_service._INCOMING_KEYS)
	).mappings().all()

	expected_schema = _SYSTEMS.schema or "public"

	allowed = {
		(expected_schema, "games"),
		(expected_schema, "game_system_rules_drafts"),
		(expected_schema, "game_system_rules_versions"),
	}

	for reference in references:
		identity = (
			reference["source_schema"],
			reference["source_table"],
		)

		if (
				identity in allowed
				and reference["target_schema"] == expected_schema
		):
			continue

		source_columns = reference["source_columns"]
		target_columns = reference["target_columns"]

		source = table(
			reference["source_table"],
			*[column(name) for name in source_columns],
			schema=reference["source_schema"],
		)

		matching_key = and_(*[
			source.c[source_name] == _SYSTEMS.c[target_name]
			for source_name, target_name in zip(
				source_columns,
				target_columns,
			)
		])

		statement = (
			select(1)
			.select_from(source.join(_SYSTEMS, matching_key))
			.where(_SYSTEMS.c.id.in_(system_ids))
			.limit(1)
		)

		if (await session.execute(statement)).first() is not None:
			raise HTTPException(
				409,
				"Связанная система содержит дополнительный контент. "
				"Безопасное каскадное удаление этого контента "
				"пока не подключено. Данные не удалены.",
			)

async def _delete_chain(session, engine_id: UUID, snapshot: dict) -> None:
	system_ids = [
		UUID(system["id"])
		for system in snapshot["systems"]
	]

	# Catalog/FK checks and deletion are in one transaction.
	# Root row locks also prevent new references to these systems.
	if system_ids:
		await session.execute(
			select(_SYSTEMS.c.id)
			.where(_SYSTEMS.c.id.in_(system_ids))
			.order_by(_SYSTEMS.c.id)
			.with_for_update()
		)

	await _reject_extra_system_content(
		session,
		system_ids,
	)

	for game in snapshot["games"]:
		staged = await game_deletion_service._stage_game_deletion(
			session,
			UUID(game["id"]),
			UUID(game["master_id"]),
		)

		if not staged:
			raise HTTPException(
				409,
				"Состав игр изменился. Обновите план операции.",
			)

	# Games referencing system publications are already deleted.
	if system_ids:
		await session.execute(
			delete(_SYSTEM_DRAFTS)
			.where(_SYSTEM_DRAFTS.c.system_id.in_(system_ids))
		)
		await session.execute(
			delete(_SYSTEM_VERSIONS)
			.where(_SYSTEM_VERSIONS.c.system_id.in_(system_ids))
		)
		await session.execute(
			delete(_SYSTEMS)
			.where(_SYSTEMS.c.id.in_(system_ids))
		)

	# A transaction-local, engine-specific trigger allowance.
	await session.execute(
		text("""
            SELECT set_config(
                'worldloom.removing_engine_id',
                :engine_id,
                true
            )
        """),
		{"engine_id": str(engine_id)},
	)

	await session.execute(
		delete(_ENGINE_VERSIONS)
		.where(_ENGINE_VERSIONS.c.engine_id == engine_id)
	)

	# Close the allowance before committing.
	await session.execute(
		text("""
            SELECT set_config(
                'worldloom.removing_engine_id',
                '',
                true
            )
        """)
	)

	# Engine draft is removed by the existing DB cascade.
	await session.execute(
		delete(_ENGINES)
		.where(_ENGINES.c.id == engine_id)
	)

async def _deactivate_chain(session, engine_id: UUID, snapshot: dict) -> None:
	system_ids = [
		UUID(system["id"])
		for system in snapshot["systems"]
	]

	await session.execute(
		update(_ENGINES)
		.where(_ENGINES.c.id == engine_id)
		.values(is_active=False)
	)

	if system_ids:
		await session.execute(
			update(_SYSTEMS)
			.where(_SYSTEMS.c.id.in_(system_ids))
			.values(is_active=False)
		)

def _sqlstate(error: DBAPIError):
	original = error.orig
	code = (
			getattr(original, "sqlstate", None)
			or getattr(original, "pgcode", None)
	)

	if code:
		return code

	cause = getattr(original, "__cause__", None)

	return (
			getattr(cause, "sqlstate", None)
			or getattr(cause, "pgcode", None)
	)

async def execute_removal(session, engine_id: UUID, actor_id: UUID, data: RuleEngineRemovalExecute) -> RuleEngineRemovalResult:
	_validate_actor(actor_id)

	try:
		await _lock_graph(session)

		snapshot = await _read_snapshot(
			session,
			engine_id,
			actor_id,
		)

		if _token(snapshot) != data.snapshot_token:
			raise HTTPException(
				409,
				"Данные изменились после предварительного просмотра. "
				"Обновите план и подтвердите действие заново.",
			)

		action = _action(snapshot)

		if action == "blocked":
			raise HTTPException(
				409,
				"Есть игры без владельца. "
				"Удаление остановлено до проверки хранилища.",
			)

		if action != data.expected_action:
			raise HTTPException(
				409,
				"Предлагаемое действие изменилось. "
				"Обновите план операции.",
			)

		if action == "delete":
			await _delete_chain(
				session,
				engine_id,
				snapshot,
			)
			result_action = "deleted"
		else:
			await _deactivate_chain(
				session,
				engine_id,
				snapshot,
			)
			result_action = "deactivated"

		response = RuleEngineRemovalResult(
			engine_id=engine_id,
			action=result_action,
			systems_count=len(snapshot["systems"]),
			games_count=len(snapshot["games"]),
			cleanup_pending=(
					action == "delete"
					and bool(snapshot["games"])
			),
		)

		# One commit for all records and all cleanup jobs.
		await session.commit()

	except DBAPIError as error:
		await session.rollback()

		code = _sqlstate(error)

		if code in {"55P03", "40P01", "57014"}:
			raise HTTPException(
				409,
				"Операция не завершена из-за занятости данных. "
				"Обновите план перед новой попыткой.",
			) from error

		if code in {"23503", "23514"}:
			raise HTTPException(
				409,
				"Операция остановлена ограничением целостности БД. "
				"Изменения этой транзакции отменены.",
			) from error

		# Do not invent a successful outcome after an unknown
		# connection/commit failure. Never retry automatically.
		raise

	except Exception:
		await session.rollback()
		raise

	# No filesystem operations here.
	# Saved jobs are processed by the existing cleanup worker.
	return response