# backend/app/Schemas/character.py

from Config.imports import (BaseModel, Field, ConfigDict, Optional, datetime, UUID)


# --- Ability scores (сила, ловкость, телосложение, интеллект, мудрость, харизма) ---

class AbilityScoreIn(BaseModel):
	characteristic_id: UUID
	base_value: int = Field(ge=1, le=30)
	bonus: int = Field(default=0, ge=-10, le=10)

class AbilityScoreRead(AbilityScoreIn):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	final_value: int
	modifier: int  # (final_value - 10) // 2, считается в сервисе

# --- Инвентарь листа ---

class InventoryItemIn(BaseModel):
	item_id: UUID
	quantity: int = 1
	custom_name: Optional[str] = None

class InventoryItemUpdate(BaseModel):
	quantity: Optional[int] = None
	is_attuned: Optional[bool] = None
	is_equipped: Optional[bool] = None
	equipped_slot: Optional[str] = None
	ammo_count: Optional[int] = None
	charges_current: Optional[int] = None
	custom_name: Optional[str] = None
	notes_json: Optional[dict] = None

class InventoryItemRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)
	sheet_id: UUID
	item_id: UUID
	quantity: int
	is_attuned: bool
	is_equipped: bool
	equipped_slot: Optional[str]
	ammo_count: Optional[int]
	charges_current: Optional[int]
	custom_name: Optional[str]

# --- Заклинания ---

class SpellOnSheetIn(BaseModel):
	spell_id: UUID
	is_known: bool = True
	is_prepared: bool = False

class SpellOnSheetUpdate(BaseModel):
	is_known: Optional[bool] = None
	is_prepared: Optional[bool] = None

class SpellOnSheetRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)
	id: UUID
	spell_id: UUID
	is_known: bool
	is_prepared: bool

class SpellSlotsUpdate(BaseModel):
	slots: dict[str, dict[str, int]]  # {"1": {"max": 4, "used": 1}}

# --- Character: "шаблон" персонажа вне конкретной игры ---

class CharacterCreate(BaseModel):
	name: str = Field(min_length=1, max_length=120)
	race_id: UUID
	background_id: Optional[UUID] = None
	level: int = Field(default=1, ge=1, le=20)
	experience: int = Field(default=0, ge=0)
	hp_max: int = Field(ge=1)

class CharacterUpdate(BaseModel):
	name: Optional[str] = Field(default=None, min_length=1, max_length=120)
	race_id: Optional[UUID] = None
	background_id: Optional[UUID] = None
	level: Optional[int] = Field(default=None, ge=1, le=20)
	experience: Optional[int] = Field(default=None, ge=0)
	hp_max: Optional[int] = Field(default=None, ge=1)

class CharacterRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	owner_id: UUID
	name: str
	race_id: UUID
	background_id: Optional[UUID]
	level: int
	experience: int
	hp_max: int
	created_at: datetime
	stats_json: dict
	saves_json: dict
	skills_json: dict
	spell_slots_json: dict
	spells: list[SpellOnSheetRead]

# --- CharacterSheet: конкретный игровой лист (в партии или НПС) ---

class CharacterSheetCreate(BaseModel):
	character_id: UUID
	game_id: UUID
	party_id: Optional[UUID] = None
	npc_id: Optional[UUID] = None
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

	id: UUID
	character_id: UUID
	game_id: UUID
	party_id: Optional[UUID]
	npc_id: Optional[UUID]
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