# backend/app/Schemas/rule_engine_lifecycle.py

"""Контракты жизненного цикла движков."""

from Config.imports import Field, Literal, UUID
from backend.app.Schemas.game_rules import RulesModel


class RuleEngineRemovalPreview(RulesModel):
	engine_id: UUID
	engine_name: str

	versions_count: int = Field(ge=0)
	systems_count: int = Field(ge=0)
	games_count: int = Field(ge=0)
	sessions_count: int = Field(ge=0)
	unowned_games_count: int = Field(ge=0)

	proposed_action: Literal["delete", "deactivate", "blocked"]