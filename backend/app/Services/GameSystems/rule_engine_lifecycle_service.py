# backend/app/Services/GameSystems/rule_engine_lifecycle_service.py

"""Предварительный расчёт удаления или деактивации движка.

Не изменяет данные, не фиксирует и не откатывает транзакцию.

Проверка административной роли и разрешения CONTENT выполняется
маршрутом. actor_id передаётся только из аутентификации.

На этом этапе сохраняем существующее ограничение:
операция доступна только владельцу движка.
"""

from Config.imports import (AsyncSession, HTTPException, UUID, func, select)
from backend.app.Database._models import (Game, GameSystem, GameSystemRulesDraft, GameSystemRulesVersion, RuleEngine, RuleEngineVersion, Session as GameSession)
from backend.app.Schemas.rule_engine_lifecycle import (RuleEngineRemovalPreview)


_ENGINES = RuleEngine.__table__
_ENGINE_VERSIONS = RuleEngineVersion.__table__
_SYSTEMS = GameSystem.__table__
_SYSTEM_DRAFTS = GameSystemRulesDraft.__table__
_SYSTEM_VERSIONS = GameSystemRulesVersion.__table__
_GAMES = Game.__table__
_SESSIONS = GameSession.__table__

def _count_rows(source):
	return (
		select(func.count())
		.select_from(source)
		.scalar_subquery()
	)

def _preview_statement(engine_id: UUID, actor_id: UUID):
	engine_versions = (
		select(_ENGINE_VERSIONS.c.id)
		.where(_ENGINE_VERSIONS.c.engine_id == engine_id)
		.cte("removal_engine_versions")
	)

	# UNION, а не UNION ALL:
	# одна система учитывается только один раз, даже если
	# связана с движком и черновиком, и несколькими публикациями.
	origin_systems = (
		select(_SYSTEM_DRAFTS.c.system_id)
		.select_from(
			_SYSTEM_DRAFTS.join(
				engine_versions,
				_SYSTEM_DRAFTS.c.engine_version_id
				== engine_versions.c.id,
				)
		)
		.union(
			select(_SYSTEM_VERSIONS.c.system_id)
			.select_from(
				_SYSTEM_VERSIONS.join(
					engine_versions,
					_SYSTEM_VERSIONS.c.engine_version_id
					== engine_versions.c.id,
					)
			)
		)
		.cte("removal_origin_systems")
	)

	linked_systems = (
		select(_SYSTEMS.c.id)
		.where(
			_SYSTEMS.c.id.in_(
				select(origin_systems.c.system_id)
			)
		)
		.cte("removal_linked_systems")
	)

	linked_games = (
		select(
			_GAMES.c.id,
			_GAMES.c.master_id,
		)
		.where(
			_GAMES.c.system_id.in_(
				select(linked_systems.c.id)
			)
		)
		.cte("removal_linked_games")
	)

	# В текущем API запись сессии создаётся при её запуске.
	# Завершённые сессии также учитываем:
	# фильтра is_active здесь намеренно нет.
	linked_sessions = (
		select(_SESSIONS.c.id)
		.where(
			_SESSIONS.c.game_id.in_(
				select(linked_games.c.id)
			)
		)
		.cte("removal_linked_sessions")
	)

	unowned_count = (
		select(func.count())
		.select_from(linked_games)
		.where(linked_games.c.master_id.is_(None))
		.scalar_subquery()
	)

	# Весь состав и все счётчики читаются одним SQL-оператором.
	# В PostgreSQL они относятся к одному снимку этого запроса.
	return (
		select(
			_ENGINES.c.id.label("engine_id"),
			_ENGINES.c.name.label("engine_name"),
			_count_rows(engine_versions).label("versions_count"),
			_count_rows(linked_systems).label("systems_count"),
			_count_rows(linked_games).label("games_count"),
			_count_rows(linked_sessions).label("sessions_count"),
			unowned_count.label("unowned_games_count"),
		)
		.where(
			_ENGINES.c.id == engine_id,
			_ENGINES.c.owner_id == actor_id,
			)
	)

async def preview_engine_removal(session: AsyncSession, engine_id: UUID, actor_id: UUID) -> RuleEngineRemovalPreview:
	if not isinstance(actor_id, UUID):
		raise HTTPException(
			status_code=401,
			detail="Требуется авторизованный пользователь.",
		)

	result = await session.execute(
		_preview_statement(engine_id, actor_id)
	)
	row = result.mappings().one_or_none()

	if row is None:
		# Сохраняем действующую политику доступа:
		# не раскрываем чужой движок.
		raise HTTPException(
			status_code=404,
			detail="Движок не найден.",
		)

	if row["sessions_count"] > 0:
		action = "deactivate"
	elif row["unowned_games_count"] > 0:
		action = "blocked"
	else:
		action = "delete"

	return RuleEngineRemovalPreview.model_validate({
		**dict(row),
		"proposed_action": action,
	})