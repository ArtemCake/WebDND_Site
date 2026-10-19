# backend/app/Schemas/content.py

from Config.imports import (
	BaseModel,
	ConfigDict,
	Field,
	Optional,
	UUID,
	datetime,
	field_validator,
)


class GameSystemRead(BaseModel):
	id: UUID
	name: str
	slug: str
	description: Optional[str] = None

	class Config:
		from_attributes = True

class GameSystemAdminRead(GameSystemRead):
	rules_engine_version: str
	is_active: bool
	created_at: datetime
	updated_at: datetime

class GameSystemCreate(BaseModel):
	model_config = ConfigDict(
		str_strip_whitespace=True,
		extra="forbid",
	)

	name: str = Field(min_length=1, max_length=100)
	slug: str = Field(
		min_length=1,
		max_length=100,
		pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
	)
	description: Optional[str] = None
	rules_engine_version: str = Field(
		default="1.0",
		min_length=1,
		max_length=20,
	)
	is_active: bool = Field(default=True, strict=True)

class GameSystemUpdate(BaseModel):
	model_config = ConfigDict(
		str_strip_whitespace=True,
		extra="forbid",
	)

	name: Optional[str] = Field(
		default=None,
		min_length=1,
		max_length=100,
	)
	slug: Optional[str] = Field(
		default=None,
		min_length=1,
		max_length=100,
		pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
	)
	description: Optional[str] = None
	rules_engine_version: Optional[str] = Field(
		default=None,
		min_length=1,
		max_length=20,
	)
	is_active: Optional[bool] = Field(default=None, strict=True)

	@field_validator(
		"name",
		"slug",
		"rules_engine_version",
		"is_active",
		mode="before",
	)
	@classmethod
	def reject_explicit_null(cls, value):
		if value is None:
			raise ValueError("Поле не может иметь значение null")
		return value