# app/database/models/Character_models.py

from Config.imports import (
	Integer, String, Index, Boolean, JSONB, ForeignKey, Table, Column,
	relationship, datetime, DateTime, func, Mapped, mapped_column)
from app.database.database import Base


# --- СВЯЗУЮЩИЕ МОДЕЛИ ---

character_conditions = Table(
	'character_conditions', Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('condition_id', Integer, ForeignKey('conditions.id', ondelete="CASCADE"), primary_key=True)
)

class CharacterClassLink(Base):
	"""
	Связующая таблица для реализации мультиклассирования.
	Один персонаж может иметь много записей здесь (Воин 3 / Плут 2).
	"""
	__tablename__ = "character_classes"

	character_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("characters.id", ondelete="CASCADE"),
		primary_key=True
	)
	class_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("classes.id", ondelete="RESTRICT"),
		primary_key=True
	)
	subclass_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("subclasses.id", ondelete="SET NULL"),
		nullable=True
	)
	level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

	character: Mapped["Character"] = relationship(back_populates="class_links")
	base_class: Mapped["Class"] = relationship(back_populates="characters")
	subclass: Mapped["Subclass | None"] = relationship()

	def __repr__(self) -> str:
		sc_name = f" ({self.subclass.name})" if self.subclass else ""
		return f"<CharClass(char_id={self.character_id}, cls={self.base_class.name}{sc_name}, lvl={self.level})>"

class CharacterSpell(Base):
	__tablename__ = "character_spells"

	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
	)
	spell_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("spells.id", ondelete="CASCADE"), primary_key=True
	)

	# Опционально: уровень, на котором персонаж выучил заклинание, или слот
	learned_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
	slot_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

	character: Mapped["Character"] = relationship(back_populates="spells")
	spell: Mapped["Spell"] = relationship(back_populates="character_spells")

	def __repr__(self) -> str:
		return f"<CharacterSpell(char_id={self.character_id}, spell_id={self.spell_id})>"

class Character(Base):
	"""
	Основная игровая сущность.
	Поддерживает мультиклассирование через character_classes и кастомные правила расчета.
	"""
	__tablename__ = "characters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)
	campaign_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	active_effects: Mapped[list["ActiveEffect"]] = relationship(
		back_populates="character",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
	level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
	experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

	# Базовые характеристики (6 шт по D&D/Pathfinder)
	strength: Mapped[int] = mapped_column(Integer, default=10)
	dexterity: Mapped[int] = mapped_column(Integer, default=10)
	constitution: Mapped[int] = mapped_column(Integer, default=10)
	intelligence: Mapped[int] = mapped_column(Integer, default=10)
	wisdom: Mapped[int] = mapped_column(Integer, default=10)
	charisma: Mapped[int] = mapped_column(Integer, default=10)

	# Производные значения для оптимизации чтения
	proficiency_bonus: Mapped[int] = mapped_column(Integer, default=2)
	armor_class: Mapped[int] = mapped_column(Integer, default=10)
	initiative: Mapped[int] = mapped_column(Integer, default=0)
	speed: Mapped[int] = mapped_column(Integer, default=30)

	current_hp: Mapped[int] = mapped_column(Integer, nullable=False)
	temp_hp: Mapped[int] = mapped_column(Integer, default=0)
	max_hp: Mapped[int] = mapped_column(Integer, nullable=False)

	death_saves_success: Mapped[int] = mapped_column(Integer, default=0)
	death_saves_failure: Mapped[int] = mapped_column(Integer, default=0)

	# Справочные связи
	race_id: Mapped[int | None] = mapped_column(ForeignKey("races.id", ondelete="SET NULL"), nullable=True, index=True)
	background_id: Mapped[int | None] = mapped_column(ForeignKey("backgrounds.id", ondelete="SET NULL"), nullable=True, index=True)

	# Кастомная иконка/токен игрока
	token_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

	# Режим домашних правил конкретно для этого персонажа
	is_homebrew_character: Mapped[bool] = mapped_column(Boolean(), default=False)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

	# --- СВЯЗИ ---
	owner: Mapped["User | None"] = relationship(
		back_populates="characters",
		foreign_keys=[user_id],
		lazy="selectin"
	)

	campaign: Mapped["Campaign | None"] = relationship(back_populates="characters")

	race: Mapped["Race | None"] = relationship()
	background: Mapped["Background | None"] = relationship()

	class_links: Mapped[list[CharacterClassLink]] = relationship(
		back_populates="character",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	spells: Mapped[list["CharacterSpell"]] = relationship(
		"CharacterSpell",
		back_populates="character",
		cascade="all, delete-orphan"
	)

	conditions: Mapped[list["Condition"]] = relationship(
		"Condition",
		secondary="character_conditions",
		back_populates="characters",
		cascade="all",
		passive_deletes=True
	)

	inventory_items: Mapped[list["InventoryItem"]] = relationship(
		"InventoryItem",
		back_populates="character",
		cascade="all, delete-orphan"
	)

	currency: Mapped["CurrencyPouch"] = relationship(
		uselist=False,
		back_populates="character",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	resistances: Mapped[list["Resistance"]] = relationship(
		back_populates="character",
		cascade="all",
		passive_deletes=True
	)

	ability_scores: Mapped[list["CharacterAbilityValue"]] = relationship(
		back_populates="character",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	traits: Mapped[list["Trait"]] = relationship(
		secondary="character_traits",
		back_populates="characters",
		lazy="selectin"
	)

	def __repr__(self) -> str:
		classes_str = ", ".join([f"{link.base_class.name} {link.level}" for link in self.class_links])
		return f"<Character(id={self.id}, name='{self.name}', LvL={self.level}, Classes=[{classes_str}])>"

class InventoryItem(Base):
	"""
	Связующая таблица Персонаж <-> Предмет.
	Реализует механику стаков (quantity) и экипировки (is_equipped).
	"""
	__tablename__ = "inventory_items"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	character_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("characters.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)
	item_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("items.id", ondelete="RESTRICT"),
		nullable=False,
		index=True
	)

	quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
	is_equipped: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)

	slot: Mapped[str | None] = mapped_column(String(50), nullable=True) # Main Hand, Backpack, Ring
	properties_override: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # Кастомизация конкретного экземпляра (зелье лечит на d8+3 вместо d4+2)

	character: Mapped["Character"] = relationship(back_populates="inventory_items")
	item: Mapped["Item"] = relationship(back_populates="inventory_slots")

	__table_args__ = (
		Index('ix_inventory_unique_stack', 'character_id', 'item_id', 'slot', unique=True),
	)

	def __repr__(self) -> str:
		equip_status = "[E]" if self.is_equipped else "[U]"
		return f"<InvItem(char={self.character_id}, item={self.item.name}, qty={self.quantity} {equip_status})>"

class CurrencyPouch(Base):
	"""
	Кошелек персонажа. Вынесен в отдельную сущность 1-к-1 для атомарных транзакций.
	Валюта хранится в медяках для упрощения математики без float.
	"""
	__tablename__ = "currency_pouches"

	character_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("characters.id", ondelete="CASCADE"),
		primary_key=True
	)

	copper: Mapped[int] = mapped_column(Integer, default=0)
	silver: Mapped[int] = mapped_column(Integer, default=0)
	electrum: Mapped[int] = mapped_column(Integer, default=0)
	gold: Mapped[int] = mapped_column(Integer, default=0)
	platinum: Mapped[int] = mapped_column(Integer, default=0)

	character: Mapped["Character"] = relationship(back_populates="currency")

	@property
	def total_copper(self) -> int:
		"""Возвращает общую сумму всех монет в пересчете на медяки."""
		rates = {"platinum": 1000, "gold": 100, "electrum": 50, "silver": 10}
		total = self.copper
		for metal, rate in rates.items():
			total += getattr(self, metal) * rate
		return total

	def __repr__(self) -> str:
		return f"<Currency(char={self.character_id}, Total cp={self.total_copper})>"