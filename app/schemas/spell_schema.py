# app/schemas/spell_schema.py

from Config.imports import List, Optional,BaseModel, Field, Dict

class CharacterSpellLink(BaseModel):
	"""Схема для связи конкретного персонажа с этим заклинанием."""
	character_id: int
	is_prepared: bool = False
	spell_slot_level_used: Optional[int] = None # Уровень ячейки, которую потратил чародей

class SpellLinks(BaseModel):
	classes: Optional[List[int]] = None
	damage_types: Optional[List[int]] = None
	# Новая связь:
	characters: Optional[List[CharacterSpellLink]] = None

class ClassMini(BaseModel):
	"""Упрощенная модель Класса для отображения внутри заклинания."""
	id: int
	name: str

	class Config:
		from_attributes = True

class DamageTypeMini(BaseModel):
	"""Упрощенная модель Типа урона."""
	id: int
	name: str

	class Config:
		from_attributes = True


class SpellCreate(BaseModel):
	"""
	Схема данных для создания нового заклинания через HTML-форму или API.
	Охватывает все скалярные поля таблицы 'spells'.
	"""

	# --- ОСНОВНЫЕ ИДЕНТИФИКАТОРЫ ---
	name: str = Field(..., min_length=1, max_length=100, description="Название заклинания")
	level: int = Field(..., ge=0, le=9, description="Уровень (0 для заговоров)")
	school: str = Field(..., description="Школа магии (Воплощение, Некромантия и т.д.)")

	# --- ОПИСАНИЕ И МЕХАНИКА ---
	description: str = Field(..., description="Полный текст описания эффекта")
	higher_levels: Optional[str] = Field(None, description="Эффект на ячейках выше уровнем")

	casting_time: Optional[str] = Field(None, example="1 действие")
	range_: Optional[str] = Field(None, example="На себя (30 футов)")
	components: Optional[str] = Field(None, example="V, S, M (кусочек фосфора)")
	duration: Optional[str] = Field(None, example="Концентрация, до 1 минуты")

	# --- БУЛЕВЫ ФЛАГИ (Чекбоксы) ---
	is_ritual: bool = Field(False, description="Является ли ритуалом")
	concentration: bool = Field(False, description="Требует ли концентрации")
	is_homebrew: bool = Field(False, description="Доморощенное правило (Homebrew)")
	homebrew_rules: Optional[Dict] = Field(None, description="JSON с правилами хоумбрю, если применимо")

	# --- СВЯЗИ (Через ID связанных таблиц) ---
	links: Optional[SpellLinks] = Field(default_factory=SpellLinks)

	class Config:
		"""Настройки схемы."""
		extra_forbid = True  # Запрещает передавать лишние/неизвестные поля

# Схема для обновления (все поля опциональны, чтобы можно было менять только часть)
class SpellUpdate(BaseModel):
	"""
	Схема для обновления заклинания.
	Все поля опциональны, так как мы передаем только измененные данные.
	"""
	# Скалярные поля
	name: Optional[str] = Field(None, min_length=1, max_length=100)
	level: Optional[int] = Field(None, ge=0, le=9)
	school_of_magic: Optional[str] = None
	description: Optional[str] = None

	casting_time: Optional[str] = None
	range_: Optional[str] = None
	components: Optional[str] = None
	duration: Optional[str] = None
	higher_levels: Optional[str] = None

	is_ritual: Optional[bool] = None
	concentration: Optional[bool] = None
	is_enabled: Optional[bool] = None
	is_homebrew: Optional[bool] = None
	homebrew_rules: Optional[Dict] = None

	# Связи (для полной замены списков ID)
	links: Optional[SpellLinks] = None

	class Config:
		extra_forbid = True

# Схема для ответа (то, что уходит во фронтенд)
class SpellRead(SpellCreate):
	"""
	Полная схема для чтения данных.
	Наследует все поля от SpellCreate + добавляет PK и раскрытые связи.
	"""
	id: int

	# Раскрываем связи через мини-схемы благодаря orm_mode
	classes: Optional[List[ClassMini]] = Field(
		default=None,
		description="Список классов, имеющих доступ к заклинанию"
	)
	damage_types: Optional[List[DamageTypeMini]] = Field(
		default=None,
		description="Список типов урона, если применимо"
	)

	class Config:
		# Разрешает создавать схему напрямую из объекта SQLAlchemy (db_obj)
		from_attributes = True
		# Позволяет сопоставлять поле 'range' в схеме со столбцом 'range_' в модели
		populate_by_name = True
		# Исключает приватные атрибуты ORM (_sa_instance_state) из сериализации
		validate_by_name = True