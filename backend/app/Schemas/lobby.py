# backend/app/Schemas/lobby.py

from Config.imports import (BaseModel, Field, Literal, Optional, UUID, datetime)


GameStatus = Literal["draft", "active", "archived"]
PrivacyLevel = Literal["public", "friends_only", "invite_only", "private"]
PartyRole = Literal["player", "assistant_dm", "banned"]


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
	master_id: UUID
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