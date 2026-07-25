# app/database/models/inventory.py

from Config.imports import (
	DateTime, func, SQLEnum, Float, CheckConstraint,
	Integer, String, Text, Boolean, ForeignKey, SmallInteger,
	relationship, JSON, datetime, Mapped, mapped_column, backref
)
from app.database.database import Base
from app.enums.person_enums import ProtectionType


class EquipmentSlot(Base):
	"""Слоты для экипировки (слот оружия, слот брони, кольца и т.д.)"""
	__tablename__ = "equipment_slots"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	slot_type: Mapped[str] = mapped_column(String(20), nullable=False) # weapon, armor, ring, etc.
	max_items: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

	equipment: Mapped[list["Equipment"]] = relationship("Equipment", backref="slot")

	def __repr__(self) -> str:
		return f"<EquipmentSlot(id={self.id}, name='{self.name}', type='{self.slot_type}')>"

class DamageType(Base):
	"""Типы урона (Огонь, Рубящий, Яд и т.д.)"""
	__tablename__ = "damage_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self) -> str:
		return f"<DamageType(id={self.id}, name='{self.name}')>"

class Equipment(Base):
	"""
	Снаряжение — конкретные экземпляры предметов в сумке или на теле.
	Это связующая таблица между Character <-> Item с дополнительными полями состояния.
	"""
	__tablename__ = "equipment"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	item_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
	)
	character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey('characters.id', ondelete="SET NULL"), nullable=True, index=True
	)

	slot_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey('equipment_slots.id'), nullable=True, index=True
	)

	name_override: Mapped[str | None] = mapped_column(String(100), nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)

	current_durability: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	charges: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

	protection_type: Mapped[ProtectionType | None] = mapped_column(
		SQLEnum(ProtectionType, native_enum=True, create_constraint=False), nullable=True
	)
	ac_bonus: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	damage_dice: Mapped[str | None] = mapped_column(String(20), nullable=True)

	# Тип урона хранится строкой (slug), чтобы избежать сложной связи М2М здесь
	damage_type_slug: Mapped[str | None] = mapped_column(String(20), nullable=True)

	magical_effects: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	is_identified: Mapped[bool] = mapped_column(Boolean(), default=False)

	requires_attunement: Mapped[bool] = mapped_column(Boolean(), default=False)
	attunement_by_class: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	attunement_by_race: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	resale_value_modifier: Mapped[float] = mapped_column(Float, default=1.0)

	# --- Связи ---
	item: Mapped["Item"] = relationship("Item") # Lazyload по умолчанию 'select'
	slot: Mapped["EquipmentSlot | None"] = relationship("EquipmentSlot", back_populates="equipment")

	# Рекурсивная связь для вложенных предметов (внутри мешочков, сундуков)
	contained_items: Mapped[list["Equipment"]] = relationship(
		"Equipment",
		secondary="container_items",
		primaryjoin=(id == "container_items.c.container_equipment_id"),
		secondaryjoin=(id == "container_items.c.item_equipment_id"),
		lazy="selectin",
		backref=backref("parent_container", uselist=False, remote_side=[id])
	)

	damage_types: Mapped[list["DamageType"]] = relationship(
		secondary="equipment_damage_types",
		backref="equipment_items",
		lazy="selectin"
	)

	character: Mapped["Character | None"] = relationship(
		"Character",
		back_populates="equipment",
		foreign_keys=[character_id],
		passive_deletes=True
	)

	def __repr__(self) -> str:
		display_name = self.name_override or self.item.name if self.item else "Unknown Item"
		owner = f"char_id={self.character_id}" if self.character_id else "storage"
		return f"<Equip(id={self.id}, name='{display_name}', owner={owner})>"

class CurrencyType(Base):
	"""Типы валюты (CP, SP, GP, Platinum, экзотические монеты)"""
	__tablename__ = "currency_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	symbol: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False)
	conversion_to_gp: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
	is_standard: Mapped[bool] = mapped_column(Boolean(), default=True)

	wallets: Mapped[list["CharacterWallet"]] = relationship("CharacterWallet", back_populates="currency")

	def __repr__(self) -> str:
		return f"<CurrencyType(symbol='{self.symbol}', gp_value={self.conversion_to_gp})>"

class CharacterWallet(Base):
	"""Кошелёк персонажа: баланс по каждой валюте отдельно."""
	__tablename__ = "character_wallets"

	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
	)
	currency_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("currency_types.id", ondelete="CASCADE"), primary_key=True
	)
	amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

	character: Mapped["Character"] = relationship("Character")
	currency: Mapped["CurrencyType"] = relationship(back_populates="wallets")

	__table_args__ = (
		CheckConstraint("amount >= 0", name="ck_wallet_amount_non_negative"),
	)

	def __repr__(self) -> str:
		return f"<CharacterWallet(char={self.character_id}, cur='{self.currency.symbol}', amt={self.amount})>"

class TransactionLog(Base):
	"""Журнал транзакций (покупки, награды, штрафы, изъятие мастером)."""
	__tablename__ = "transaction_logs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True
	)
	shop_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("shops.id", ondelete="SET NULL"), nullable=True, index=True
	)
	dm_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
	currency_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("currency_types.id", ondelete="RESTRICT"), nullable=False
	)
	amount: Mapped[int] = mapped_column(Integer, nullable=False)

	item_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("items.id", ondelete="SET NULL"), nullable=True
	)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)

	timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- Связи ---
	character: Mapped["Character | None"] = relationship("Character")
	shop: Mapped["ShopVendor | None"] = relationship("ShopVendor")
	dm: Mapped["User | None"] = relationship("User")
	currency: Mapped["CurrencyType"] = relationship()
	item: Mapped["Item | None"] = relationship("Item")

	def __repr__(self) -> str:
		sign = "-" if self.amount < 0 else "+"
		return (f"<TransactionLog(type='{self.transaction_type}', {sign}{abs(self.amount)} "
		        f"'{self.currency.symbol}' at {self.timestamp.isoformat()})>")