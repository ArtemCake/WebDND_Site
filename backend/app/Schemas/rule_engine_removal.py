# backend/app/Schemas/rule_engine_removal.py

from Config.imports import (UUID, Literal, Field)
from backend.app.Schemas.game_rules import RulesModel
from backend.app.Schemas.rule_engine_lifecycle import (RuleEngineRemovalPreview)


class RuleEngineRemovalPlan(RuleEngineRemovalPreview):
	snapshot_token: str = Field(
		min_length=64,
		max_length=64,
		pattern=r"^[0-9a-f]{64}$",
	)

class RuleEngineRemovalExecute(RulesModel):
	snapshot_token: str = Field(
		min_length=64,
		max_length=64,
		pattern=r"^[0-9a-f]{64}$",
	)
	expected_action: Literal["delete", "deactivate"]

class RuleEngineRemovalResult(RulesModel):
	engine_id: UUID
	action: Literal["deleted", "deactivated"]
	systems_count: int = Field(ge=0)
	games_count: int = Field(ge=0)
	cleanup_pending: bool
