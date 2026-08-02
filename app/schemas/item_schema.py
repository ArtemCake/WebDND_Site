# app/schemas/item_schema.py

from Config.imports import  Optional,BaseModel
from app.enums.person_enums import ItemType, ItemRarity


class ItemCreate(BaseModel):
	name: str
	type: ItemType
	rarity: Optional[ItemRarity] = ItemRarity.COMMON
	cost: Optional[int] = 0
	weight: Optional[float] = 0.0
	attunement: bool = False
	description: Optional[str]

class ItemUpdate(BaseModel):
	name: Optional[str]
	type: Optional[ItemType]
	rarity: Optional[ItemRarity]
	cost: Optional[int]
	weight: Optional[float]
	attunement: Optional[bool]
	description: Optional[str]

	class Config:
		extra_forbid = True

class ItemRead(ItemCreate):
	id: int
	class Config:
		orm_mode = True