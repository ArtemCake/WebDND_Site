# app/enums/person_enums.py

from Config.imports import (enum, Optional, Any, Dict, PG_ENUM, SchemaType)


class ItemCategory(str, enum.Enum):
	"""Категории предметов инвентаря."""
	WEAPON = "weapon"
	ARMOR = "armor"
	GEAR = "gear"  # Свитки, зелья, компоненты
	WONDROUS_ITEM = "wondrous_item"

	def __str__(self) -> str:
		return self.value

class ProtectionType(str, enum.Enum):
	"""Типы взаимодействия с уроном (сопротивления и т.д.)."""
	RESISTANCE = "resistance"
	VULNERABILITY = "vulnerability"
	IMMUNITY = "immunity"

	def multiplier(self) -> float:
		"""Возвращает множитель для расчета входящего урона данного типа."""
		if self == ProtectionType.RESISTANCE:
			return 0.5
		if self == ProtectionType.IMMUNITY:
			return 0.0
		if self == ProtectionType.VULNERABILITY:
			return 2.0
		return 1.0

	def __str__(self) -> str:
		return self.value

class PreparationStatus(str, enum.Enum):
	"""Статус подготовки заклинаний или способностей."""
	KNOWN = "known"       # Известно (у чародеев/чернокнижников)
	PREPARED = "prepared" # Подготовлено (у жрецов/волшебников)
	BOTH = "both"         # Универсальный тип (кантрипы)

	def __str__(self) -> str:
		return self.value

class ProficiencyType(str, enum.Enum):
	"""Тип владения навыком или предметом."""
	WEAPON = "weapon"
	ARMOR = "armor"
	TOOL = "tool"
	SKILL = "skill"
	SAVING_THROW = "saving_throw"

	def __str__(self) -> str:
		return self.value

class MagicItemRarity(str, enum.Enum):
	"""
	Редкость магических предметов согласно правилам D&D 5e.
	Используется для определения силы предмета и его стоимости.
	"""
	COMMON = "common"       # +0..1 к характеристикам или мелкие удобства
	UNCOMMON = "uncommon"   # +2 к характеристикам, базовые зачарования оружия
	RARE = "rare"           # Существенные бонусы, сопротивляемость стихиям
	VERY_RARE = "very_rare" # Мощные артефакты, +3 к характеристикам
	LEGENDARY = "legendary" # Уникальные предметы мирового масштаба
	ARTIFACT = "artifact"   # Объекты божественной силы (Молот Тора, Око Грюма)

	def __str__(self) -> str:
		return self.value

def get_pg_enum_type(enum_class, **kwargs: Any) -> SchemaType:
	"""
	Фабричная функция для создания типов SQLAlchemy SQLEnum,
	адаптированных под PostgreSQL.

	Использование в модели:
	category = Column(get_pg_enum_type(ItemCategory), nullable=False)
	"""
	values = [item.value for item in enum_class]
	return PG_ENUM(*values, name=f"{enum_class.__name__.lower()}_enum", create_type=True, **kwargs)

def parse_enum_value(enum_class, value: Optional[str]) -> Optional[enum.Enum]:
	"""
	Безопасный парсер строки из БД в Enum-класс.
	Защищает от None и ошибок опечаток при чтении сырых данных.
	"""
	if value is None:
		return None
	try:
		return enum_class(value)
	except ValueError:
		# Логирование ошибки можно добавить здесь
		return None

def serialize_enum_for_json(enum_item: Optional[enum.Enum]) -> Optional[str]:
	"""
	Сериализация Enum для сохранения в JSON-поля БД или отправки через API.
	Возвращает строковое значение ('weapon', 'armor') или None.
	"""
	if enum_item is None:
		return None
	return enum_item.value

def deserialize_enum_from_json(enum_class, json_value: Optional[str]) -> Optional[enum.Enum]:
	"""
	Десериализация Enum из JSON-строки.
	Удобно использовать при загрузке кастомных статблоков персонажа.
	"""
	return parse_enum_value(enum_class, json_value)