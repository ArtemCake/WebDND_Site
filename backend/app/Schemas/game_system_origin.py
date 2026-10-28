# backend/app/Schemas/game_system_origin.py

"""Выбор опубликованной основы для правил игровой системы."""

from Config.imports import Any, Field, UUID
from backend.app.Schemas.content import GameSystemCreate
from backend.app.Schemas.game_rules import RulesModel
from backend.app.Schemas.rule_engines import RuleEngineVersionRead


class EngineRulesSource(RulesModel):
	engine_id: UUID = Field(strict=False)
	engine_version_id: UUID = Field(strict=False)
	rules_overrides: dict[str, Any] = Field(default_factory=dict)

class GameSystemFromEngineCreate(EngineRulesSource):
	system: GameSystemCreate

class GameSystemDraftEngineSet(EngineRulesSource):
	# null — клиент ожидает, что черновика ещё нет.
	# Число — ожидаемая ревизия существующего черновика.
	expected_revision: int | None = Field(..., ge=1)

class GameSystemEngineEditorUpdate(GameSystemDraftEngineSet):
	"""Единое обновление карточки и связанных правил."""

	system: GameSystemCreate

class GameSystemEngineOriginRead(RulesModel):
	"""Основа сохранённого черновика и ревизия его состояния."""

	draft_revision: int = Field(ge=1)
	engine_version: RuleEngineVersionRead
