# backend/app/Schemas/game_system_origin.py

"""Выбор опубликованной основы для правил игровой системы."""

from Config.imports import Any, Field, UUID
from backend.app.Schemas.content import GameSystemCreate
from backend.app.Schemas.game_rules import RulesModel


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