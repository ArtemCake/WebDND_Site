# app/schemas/monster_schema.py

from Config.imports import  Optional, BaseModel, conint, Field, confloat
from app.enums.person_enums import Size


class MonsterCreate(BaseModel):
	name: str
	size: Size
	creature_type: str
	alignment: Optional[str]
	armor_class: conint(gt=0)
	hp: conint(gt=0)
	speed: str
	strength: conint(ge=1, le=30)
	dexterity: conint(ge=1, le=30)
	constitution: conint(ge=1, le=30)
	intelligence: conint(ge=1, le=30)
	wisdom: conint(ge=1, le=30)
	charisma: conint(ge=1, le=30)
	challenge_rating: float = Field(gt=0)
	description: Optional[str]
	special_abilities: Optional[str]
	actions: Optional[str]

class MonsterUpdate(BaseModel):
	name: Optional[str] = Field(None, min_length=1, max_length=100)
	size: Optional[Size] = None
	creature_type: Optional[str] = None
	alignment: Optional[str] = None

	armor_class: Optional[conint(gt=0)] = None
	hp: Optional[conint(gt=0)] = None
	speed: Optional[str] = None

	strength: Optional[conint(ge=1, le=30)] = None
	dexterity: Optional[conint(ge=1, le=30)] = None
	constitution: Optional[conint(ge=1, le=30)] = None
	intelligence: Optional[conint(ge=1, le=30)] = None
	wisdom: Optional[conint(ge=1, le=30)] = None
	charisma: Optional[conint(ge=1, le=30)] = None

	challenge_rating: Optional[confloat(gt=0)] = None

	description: Optional[str] = None
	special_abilities: Optional[str] = None
	actions: Optional[str] = None
	legendary_actions: Optional[str] = None
	class Config:
		extra_forbid = True

class MonsterRead(MonsterCreate):
	id: int
	class Config:
		orm_mode = True