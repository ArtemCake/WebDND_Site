# backend/app/Schemas/lobby.py

from Config.imports import (BaseModel, Field, Literal, Optional, UUID, datetime)


GameStatus = Literal["draft", "active", "archived"]
PrivacyLevel = Literal["public", "friends_only", "invite_only", "private"]
PartyRole = Literal["player", "assistant_dm", "banned"]
AdvantageType = Literal["advantage", "disadvantage"]

# --- Game ---

class GameCreate(BaseModel):
	system_id: UUID
	title: str
	description: Optional[str] = None
	privacy_level: PrivacyLevel = "invite_only"
	voice_chat_config: Optional[dict] = None
	is_homebrew_allowed: bool = False

class GameUpdate(BaseModel):
	title: Optional[str] = None
	description: Optional[str] = None
	status: Optional[GameStatus] = None
	privacy_level: Optional[PrivacyLevel] = None
	voice_chat_config: Optional[dict] = None
	is_homebrew_allowed: Optional[bool] = None

class GameRead(BaseModel):
	id: UUID
	master_id: Optional[UUID]
	system_id: UUID
	title: str
	description: Optional[str]
	status: GameStatus
	privacy_level: PrivacyLevel
	voice_chat_config: Optional[dict]
	is_homebrew_allowed: bool

	class Config:
		from_attributes = True

# --- Party ---

class PartyRead(BaseModel):
	game_id: UUID
	user_id: UUID
	role_in_game: PartyRole
	is_active: bool
	notification_settings: Optional[dict]

	class Config:
		from_attributes = True

class PartyRoleUpdate(BaseModel):
	role_in_game: PartyRole

# --- Invite ---

class InviteCreate(BaseModel):
	expires_at: Optional[datetime] = None
	uses_limit: Optional[int] = Field(default=None, ge=1)
	message: Optional[str] = None

class InviteRead(BaseModel):
	token: str
	game_id: UUID
	creator_id: UUID
	claimed_by: Optional[UUID]
	expires_at: Optional[datetime]
	uses_limit: Optional[int]
	uses_current: int
	message: Optional[str]

	class Config:
		from_attributes = True

class InviteClaim(BaseModel):
	token: str

# --- Dice Roll ---

class DiceRollIn(BaseModel):
	formula: str = Field(min_length=2, max_length=100)
	advantage: Optional[AdvantageType] = None
	is_gm_hidden: bool = False
	context_type: Optional[str] = None
	context_target_id: Optional[UUID] = None

class DiceRollRead(BaseModel):
	id: UUID
	session_id: Optional[UUID]
	roller_id: Optional[UUID]
	npc_id: Optional[UUID]
	party_id: Optional[UUID]
	formula: str
	result_total: int
	individual_results: list[int]
	advantage: Optional[AdvantageType]
	is_gm_hidden: bool
	context_type: Optional[str]
	context_target_id: Optional[UUID]
	created_at: datetime

	class Config:
		from_attributes = True

class SessionCreate(BaseModel):
	title: Optional[str] = Field(default=None, max_length=255)

class SessionUpdate(BaseModel):
	title: Optional[str] = Field(default=None, max_length=255)
	summary_log: Optional[str] = None

class SessionRead(BaseModel):
	id: UUID
	game_id: UUID
	title: Optional[str]
	summary_log: Optional[str]
	start_time: datetime
	end_time: Optional[datetime]
	is_active: bool

	class Config:
		from_attributes = True
