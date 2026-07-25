# app/database/models/dnd.py

from Config.imports import (
	SQLEnum, Float,
	Integer, String, Text, Boolean, ForeignKey,
	relationship, JSON, Mapped, mapped_column)
from app.database.database import Base
from app.enums.person_enums import ItemCategory, MagicItemRarity


class Race(Base):
	"""
	Расы персонажей (Human, Elf, Dwarf и т.д.).
	Служит базовым шаблоном для HomebrewEntity.
	"""
	__tablename__ = "races"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	size: Mapped[str] = mapped_column(String(20), nullable=False)
	speed: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

	# Базовые данные расы в сыром виде для гибкости
	languages_base: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	ability_bonuses_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	traits_description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Связь с кастомными вариантами этой расы (Хоумбрю)
	homebrew_variants: Mapped[list["HomebrewEntity"]] = relationship(
		"HomebrewEntity",
		back_populates="parent_entity",
		foreign_keys="HomebrewEntity.parent_canon_id",
		primaryjoin="and_(Race.id == HomebrewEntity.parent_canon_id, "
		            "HomebrewEntity.entity_type == 'app.enums.db_enums.EntityTypeEnum.RACE')",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	def __repr__(self) -> str:
		return f"<Race(id={self.id}, name='{self.name}')>"

class Background(Base):
	"""Предыстории персонажей (Soldier, Criminal, Sage и т.д.)"""
	__tablename__ = "backgrounds"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	skills_granted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	languages_granted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	tool_proficiencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	feature_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
	feature_description: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self) -> str:
		return f"<Background(id={self.id}, name='{self.name}')>"

class Class_(Base):
	"""
	Классы персонажей. Название Class_, так как слово 'class' зарезервировано в Python.
	"""
	__tablename__ = "classes"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	hit_die: Mapped[int] = mapped_column(Integer, nullable=False)
	primary_ability: Mapped[str | None] = mapped_column(String(50), nullable=True)

	saving_throw_proficiencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	armor_proficiencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	weapon_proficiencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	tools_proficiencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	multiclass_requirements_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	subclasses: Mapped[list["Subclass"]] = relationship(
		"Subclass",
		back_populates="parent_class",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	def __repr__(self) -> str:
		return f"<Class(id={self.id}, name='{self.name}')>"

class Subclass(Base):
	"""Подклассы (Arcane Trickster, Champion, Wild Magic Sorcerer и т.д.)"""
	__tablename__ = "subclasses"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	parent_class_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("classes.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	parent_class: Mapped["Class_"] = relationship("Class_", back_populates="subclasses")

	def __repr__(self) -> str:
		return f"<Subclass(id={self.id}, name='{self.name}', class_id={self.parent_class_id})>"

class Spell(Base):
	"""Заклинания"""
	__tablename__ = "spells"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	school: Mapped[str] = mapped_column(String(30), nullable=False)
	casting_time: Mapped[str] = mapped_column(String(50), nullable=False)
	range_: Mapped[str] = mapped_column(String(50), nullable=False) # range - зарезервированное слово
	components: Mapped[str] = mapped_column(String(100), nullable=False)
	duration: Mapped[str] = mapped_column(String(50), nullable=False)

	is_ritual: Mapped[bool] = mapped_column(Boolean(), default=False)
	classes_allowed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	higher_levels: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self) -> str:
		return f"<Spell(id={self.id}, name='{self.name}', lvl={self.level})>"

class Item(Base):
	"""Предметы (общее определение, включая оружие, броню, расходники)"""
	__tablename__ = "items"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	category: Mapped[ItemCategory] = mapped_column(SQLEnum(ItemCategory, native_enum=True, create_constraint=False), nullable=False)
	rarity: Mapped[MagicItemRarity | None] = mapped_column(SQLEnum(MagicItemRarity, native_enum=True, create_constraint=False), nullable=True)

	weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
	cost_cp: Mapped[int | None] = mapped_column(Integer, nullable=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	properties_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	def __repr__(self) -> str:
		return f"<Item(id={self.id}, name='{self.name}', cat={self.category.value})>"