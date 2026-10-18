# backend/app/Schemas/maps.py

from Config.imports import (datetime, UUID, BaseModel, Field, Optional)


class TokenCreate(BaseModel):
	session_id: UUID
	current_map_id: Optional[UUID] = None
	character_sheet_id: Optional[UUID] = None
	npc_id: Optional[UUID] = None
	image_url: str = Field(max_length=1000)
	display_name: Optional[str] = Field(default=None, max_length=100)
	grid_x: int
	grid_y: int
	elevation: int = 0
	rotation_deg: float = 0.0
	hp_current: int
	hp_max: int
	conditions_json: Optional[dict] = None
	is_visible_to_players: bool = True
	controlled_by_ids: Optional[list[UUID]] = None
	vision_radius_cells: int = 6

class TokenUpdate(BaseModel):
	current_map_id: Optional[UUID] = None
	character_sheet_id: Optional[UUID] = None
	npc_id: Optional[UUID] = None
	image_url: Optional[str] = Field(default=None, max_length=1000)
	display_name: Optional[str] = Field(default=None, max_length=100)
	elevation: Optional[int] = None
	rotation_deg: Optional[float] = None
	hp_current: Optional[int] = None
	hp_max: Optional[int] = None
	conditions_json: Optional[dict] = None
	is_visible_to_players: Optional[bool] = None
	controlled_by_ids: Optional[list[UUID]] = None
	vision_radius_cells: Optional[int] = None

class TokenMove(BaseModel):
	grid_x: int
	grid_y: int
	hex_id: Optional[UUID] = None

class TokenRead(BaseModel):
	id: UUID
	session_id: UUID
	current_map_id: Optional[UUID]
	character_sheet_id: Optional[UUID]
	npc_id: Optional[UUID]
	owner_id: UUID
	image_url: str
	display_name: Optional[str]
	grid_x: int
	grid_y: int
	current_hex_id: Optional[UUID]
	vision_radius_cells: int
	elevation: int
	rotation_deg: float
	hp_current: int
	hp_max: int
	conditions_json: Optional[dict]
	is_visible_to_players: bool
	controlled_by_ids: Optional[list[UUID]]
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True

class HexGridGenerateIn(BaseModel):
	rows: int = Field(gt=0, le=200)
	cols: int = Field(gt=0, le=200)

class MapLayerRead(BaseModel):
	id: UUID
	map_id: UUID
	name: str
	layer_type: str
	z_index: int

	class Config:
		from_attributes = True

class FogOfWarRecalcIn(BaseModel):
	viewer_token_ids: list[UUID]

class FogOfWarRecalcOut(BaseModel):
	visible_hex_ids: list[UUID]

class MapCreate(BaseModel):
	game_id: UUID
	session_id: Optional[UUID] = None
	title: str = Field(max_length=255)
	map_type: str  # 'image_upload' | 'procedural_generation'
	background_image_url: Optional[str] = Field(default=None, max_length=1000)
	grid_settings_json: Optional[dict] = None
	fog_of_war_enabled: bool = True
	lighting_model: str = "basic"

class MapUpdate(BaseModel):
	title: Optional[str] = Field(default=None, max_length=255)
	background_image_url: Optional[str] = Field(default=None, max_length=1000)
	grid_settings_json: Optional[dict] = None
	fog_of_war_enabled: Optional[bool] = None
	lighting_model: Optional[str] = None

class MapRead(BaseModel):
	id: UUID
	game_id: UUID
	session_id: Optional[UUID]
	title: str
	map_type: str
	background_image_url: Optional[str]
	grid_settings_json: dict
	fog_of_war_enabled: bool
	lighting_model: str
	is_active_in_session: bool
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True