# backend/app/Schemas/content.py

from Config.imports import (BaseModel, Optional, UUID)


class GameSystemRead(BaseModel):
	id: UUID
	name: str
	slug: str
	description: Optional[str] = None

	class Config:
		from_attributes = True