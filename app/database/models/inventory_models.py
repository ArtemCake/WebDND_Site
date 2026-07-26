# app/database/models/inventory_models.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey,
	relationship, datetime, DateTime, func, Index, Mapped, mapped_column)
from app.database.database import Base


class Item(Base):
	"""
	Базовый справочник предметов.
	Может быть как обычным мечом, так и компонентом для заклинания.
	"""
	__tablename__ = "items"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	item_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # Weapon, Armor, Consumable, Tool

	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	weight: Mapped[float] = mapped_column(default=0.0) # В фунтах
	cost_copper: Mapped[int] = mapped_column(Integer, default=0) # Хранение в минимально единице (медяк) для точности расчетов

	is_stackable: Mapped[bool] = mapped_column(Boolean(), default=False)
	max_stack_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	inventory_slots: Mapped[list["InventoryItem"]] = relationship(back_populates="item")
	magic_properties: Mapped[list["MagicItemProperty"]] = relationship("MagicItemProperty", back_populates="base_item", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Item(id={self.id}, name='{self.name}', type={self.item_type}, status={status})>"

class MagicItemProperty(Base):
	"""
	Магические свойства предмета (например, бонус +1 к атаке, урон огнем).
	Позволяет на лету собирать уникальные магические предметы из базы.
	"""
	__tablename__ = "magic_item_properties"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	base_item_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("items.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	property_name: Mapped[str] = mapped_column(String(100), nullable=False)
	property_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
	property_description: Mapped[str | None] = mapped_column(Text, nullable=True)

	requires_attunement: Mapped[bool] = mapped_column(Boolean(), default=False)
	attuned_character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)

	base_item: Mapped["Item"] = relationship(back_populates="magic_properties")
	attuned_character: Mapped["Character | None"] = relationship(foreign_keys=[attuned_character_id])

	def __repr__(self) -> str:
		val = f" {self.property_value}" if self.property_value is not None else ""
		return f"<MagicProp(item_id={self.base_item_id}, name='{self.property_name}{val}')>"

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