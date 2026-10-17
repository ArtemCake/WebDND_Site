# backend/app/Schemas/character.py

from Config.imports import (BaseModel, Field, ConfigDict, Optional, datetime)


# --- Ability scores (сила, ловкость, телосложение, интеллект, мудрость, харизма) ---

class AbilityScoreIn(BaseModel):
	characteristic_id: int
	base_value: int = Field(ge=1, le=30)
	bonus: int = Field(default=0, ge=-10, le=10)

class AbilityScoreRead(AbilityScoreIn):
	model_config = ConfigDict(from_attributes=True)

	id: int
	final_value: int
	modifier: int  # (final_value - 10) // 2, считается в сервисе

# --- Инвентарь листа ---

class InventoryItemIn(BaseModel):
	equipment_id: int
	quantity: int = Field(default=1, ge=1)
	is_equipped: bool = False
	notes: Optional[str] = Field(default=None, max_length=500)

class InventoryItemRead(InventoryItemIn):
	model_config = ConfigDict(from_attributes=True)

	id: int

# --- Character: "шаблон" персонажа вне конкретной игры ---

class CharacterCreate(BaseModel):
	name: str = Field(min_length=1, max_length=120)
	race_id: int
	background_id: Optional[int] = None
	level: int = Field(default=1, ge=1, le=20)
	experience: int = Field(default=0, ge=0)
	hp_max: int = Field(ge=1)

class CharacterUpdate(BaseModel):
	name: Optional[str] = Field(default=None, min_length=1, max_length=120)
	race_id: Optional[int] = None
	background_id: Optional[int] = None
	level: Optional[int] = Field(default=None, ge=1, le=20)
	experience: Optional[int] = Field(default=None, ge=0)
	hp_max: Optional[int] = Field(default=None, ge=1)

class CharacterRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	owner_id: int
	name: str
	race_id: int
	background_id: Optional[int]
	level: int
	experience: int
	hp_max: int
	created_at: datetime

# --- CharacterSheet: конкретный игровой лист (в партии или НПС) ---

class CharacterSheetCreate(BaseModel):
	character_id: int
	party_id: Optional[int] = None
	npc_id: Optional[int] = None
	version_note: Optional[str] = Field(default=None, max_length=200)
	ability_scores: list[AbilityScoreIn] = Field(min_length=6, max_length=6)
	proficiency_bonus: int = Field(default=2, ge=2, le=6)
	hp_current: int = Field(ge=0)
	hp_temp: int = Field(default=0, ge=0)

class CharacterSheetUpdate(BaseModel):
	"""Частичное обновление — для боевых изменений за сессию (HP, состояния, спасброски от смерти)."""
	hp_current: Optional[int] = Field(default=None, ge=0)
	hp_temp: Optional[int] = Field(default=None, ge=0)
	death_save_successes: Optional[int] = Field(default=None, ge=0, le=3)
	death_save_failures: Optional[int] = Field(default=None, ge=0, le=3)
	conditions: Optional[list[str]] = None
	is_active_in_game: Optional[bool] = None

class CharacterSheetRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	character_id: int
	party_id: Optional[int]
	npc_id: Optional[int]
	version_note: Optional[str]
	proficiency_bonus: int
	hp_current: int
	hp_temp: int
	death_save_successes: int
	death_save_failures: int
	conditions: list[str]
	is_active_in_game: bool
	ability_scores: list[AbilityScoreRead]
	inventory: list[InventoryItemRead]
	created_at: datetime