# backend/app/Schemas/rule_engines.py

"""Контракты создания, сохранения и публикации движков."""

from Config.imports import Field, Literal, UUID, datetime
from backend.app.Schemas.game_rules import RulesModel, RulesProfile


class RuleEngineCreate(RulesModel):
	name: str = Field(
		min_length=1,
		max_length=100,
		pattern=r"\S",
	)
	slug: str = Field(
		min_length=1,
		max_length=100,
		pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
	)
	description: str | None = None
	visibility: Literal["private", "public"] = "private"

	rules_engine_version: str = Field(
		default="1.0",
		min_length=1,
		max_length=20,
		pattern=r"\S",
	)
	rules: RulesProfile

class RuleEngineDraftUpdate(RulesModel):
	rules: RulesProfile
	expected_revision: int = Field(ge=1)

class RuleEnginePublish(RulesModel):
	expected_revision: int = Field(ge=1)

class RuleEngineRead(RulesModel):
	id: UUID
	owner_id: UUID | None
	name: str
	slug: str
	description: str | None
	visibility: Literal["private", "public"]
	is_active: bool
	created_at: datetime
	updated_at: datetime

class RuleEngineDraftRead(RulesModel):
	id: UUID
	engine_id: UUID
	rules_json: RulesProfile
	rules_engine_version: str
	revision: int = Field(ge=1)
	created_at: datetime
	updated_at: datetime

class RuleEngineVersionRead(RulesModel):
	id: UUID
	engine_id: UUID
	version_number: int = Field(ge=1)
	source_draft_revision: int = Field(ge=1)
	rules_json: RulesProfile
	rules_engine_version: str
	published_at: datetime

class RuleEngineEditorRead(RulesModel):
	engine: RuleEngineRead
	draft: RuleEngineDraftRead