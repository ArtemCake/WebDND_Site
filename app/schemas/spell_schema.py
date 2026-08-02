# app/schemas/spell_schema.py

from Config.imports import List, Optional,BaseModel, Field


# Схема для создания нового заклинания
class SpellCreate(BaseModel):
	name: str = Field(..., min_length=1, max_length=100)
	level: int = Field(ge=0, le=9)
	school_of_magic: str
	description: str
	casting_time: Optional[str] = None
	range: Optional[str] = None
	components: Optional[str] = None
	duration: Optional[str] = None
	classes: Optional[List[int]] = None # ID классов

# Схема для обновления (все поля опциональны, чтобы можно было менять только часть)
class SpellUpdate(BaseModel):
	name: Optional[str]
	level: Optional[int]
	school_of_magic: Optional[str]
	description: Optional[str]
	casting_time: Optional[str]
	range: Optional[str]
	components: Optional[str]
	duration: Optional[str]
	classes: Optional[List[int]]

	class Config:
		extra_forbid = True # Запрещаем передавать лишние поля

# Схема для ответа (то, что уходит во фронтенд)
class SpellRead(SpellCreate):
	id: int

	class Config:
		orm_mode = True # Позволяет создавать схему прямо из объекта SQLAlchemy