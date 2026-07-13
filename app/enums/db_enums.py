# app/enums/db_enums.py

from Config.imports import (enum, Any, PG_ENUM, SchemaType)


class EntityTypeEnum(str, enum.Enum):
	"""Типы сущностей для таблицы homebrew_entities."""
	RACE = "race"
	CLASS = "class"
	SUBCLASS = "subclass"
	SPELL = "spell"
	BACKGROUND = "background"
	FEAT = "feat"
	ITEM = "item"
	MONSTER = "monster" # Для хранения кастомных монстров
	NPC_TEMPLATE = "npc_template" # Готовый блок статов для Ведущего

	def __str__(self) -> str:
		return self.value

def get_pg_enum_type(enum_class: type[enum.Enum], **kwargs: Any) -> SchemaType:
	"""
	Фабричная функция для создания типов SQLAlchemy SQLEnum,
	адаптированных под PostgreSQL с созданием типа в БД.
	"""
	values = [item.value for item in enum_class]
	return PG_ENUM(*values, name=f"{enum_class.__name__.lower()}_enum", create_type=True, **kwargs)