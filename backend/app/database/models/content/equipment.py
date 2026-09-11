# backend/app/models/content/equipment.py

"""Модели снаряжения, предметов и их иерархии."""

from Config.imports import (Mapped, mapped_column, relationship, JSONB, ARRAY, text, Float, backref,
					DateTime, String, Text, Integer, Boolean, ForeignKey, PG_UUID, uuid4, datetime)
from backend.app.database.database import Base


# --- СНАРЯЖЕНИЕ (БАЗОВЫЙ ПРЕДМЕТ) ---
class Equipment(Base):
	"""
	Базовая таблица всех предметов.
	Реализует требование ТЗ о хранении снаряжения с поддержкой Homebrew.
	"""
	__tablename__ = "equipment"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True)
	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	item_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("item_types.id"), nullable=False, index=True)
	rarity_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rarities.id"), nullable=True, index=True)
	weight: Mapped[float | None] = mapped_column(Float, nullable=True) # в фунтах
	cost: Mapped[dict | None] = mapped_column( JSONB, nullable=True, server_default=text("'{\"gp\": 0}'::jsonb") )
	# Структура: {"cp": 5, "sp": 0, "ep": 0, "gp": 10, "pp": 0}
	properties_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# e.g. {"finesse": true, "thrown": true, "range": {"normal": 20, "long": 60}}
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="equipment") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_equipment")
	type_obj: Mapped["ItemType"] = relationship("ItemType")
	rarity: Mapped["Rarity"] = relationship("Rarity")
	weapons: Mapped[list["Weapon"]] = relationship("Weapon", back_populates="base_item", cascade="all, delete-orphan")
	armor: Mapped[list["Armor"]] = relationship("Armor", back_populates="base_item", cascade="all, delete-orphan")
	magical_items: Mapped[list["MagicalItem"]] = relationship("MagicalItem", back_populates="base_item", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Equipment(id='{self.id}', name='{self.name}')>"

# --- ТИПЫ ПРЕДМЕТОВ ---
class ItemType(Base):
	"""
	Иерархический справочник типов предметов (снаряжения).
	Реализует требование ТЗ о хранении типа предмета.
	Поддерживает вложенность: Container -> Backpack, Weapon -> Martial Weapon.
	"""
	__tablename__ = "item_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True)
	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False)
	parent_type_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("item_types.id", ondelete="SET NULL"), nullable=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_gear_slot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	# True если это слот экипировки (Head, Body, Ring). False - просто категория в инвентаре.
	slot_name: Mapped[str | None] = mapped_column(String(50), nullable=True) # 'head', 'armor', 'weapon'
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="item_types") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_item_types")
	children: Mapped[list["ItemType"]] = relationship("ItemType", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
	equipment: Mapped[list["Equipment"]] = relationship("Equipment", back_populates="type_obj")

	def __repr__(self) -> str:
		return f"<ItemType(id={self.id}, name='{self.name}')>"

# --- РЕДКОСТЬ ПРЕДМЕТОВ ---
class Rarity(Base):
	"""
	Справочник уровней редкости предметов.
	Реализует требование ТЗ о хранении редкости снаряжения и артефактов.
	"""
	__tablename__ = "rarities"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True)
	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Common', 'Very Rare'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0") # Для сортировки в фильтрах UI
	color_theme: Mapped[str | None] = mapped_column(String(7), nullable=True) # HEX цвет (#1A8BFF для Uncommon)
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="rarities") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_rarities")
	equipment: Mapped[list["Equipment"]] = relationship("Equipment", back_populates="rarity")
	magical_items: Mapped[list["MagicalItem"]] = relationship("MagicalItem", back_populates="rarity")
	artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="rarity")

	def __repr__(self) -> str:
		return f"<Rarity(id={self.id}, name='{self.name}', order={self.sort_order})>"

# --- ОРУЖИЕ ---
class Weapon(Base):
	"""
	Специфические параметры оружия.
	Связаны один-к-одному с базовой таблицей equipment.
	"""
	__tablename__ = "weapons"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	base_item_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
	weapon_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("weapon_types.id"), nullable=False, index=True)
	weapon_class_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("weapon_classes.id"), nullable=True, index=True)
	# Боевая механика
	damage_dice: Mapped[str] = mapped_column(String(20), nullable=False) # e.g. '1d8', '2d6'
	damage_type_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="SET NULL"), nullable=True, index=True)
	properties_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"finesse": true, "thrown": 20, "heavy": true, "special": "Versatile (1d10)"}
	range_normal: Mapped[int | None] = mapped_column(Integer, nullable=True) # Для метательного/дистанционного
	range_long: Mapped[int | None] = mapped_column(Integer, nullable=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	base_item: Mapped["Equipment"] = relationship("Equipment", back_populates="weapons")
	type_obj: Mapped["WeaponType"] = relationship("WeaponType")
	weapon_class: Mapped["WeaponClass"] = relationship("WeaponClass")
	damage_type: Mapped["DamageType"] = relationship("DamageType")

	def __repr__(self) -> str:
		return f"<Weapon(id='{self.id}', name='{self.base_item.name}', dice='{self.damage_dice}')>"

# --- ТИПЫ ОРУЖИЯ ---
class WeaponType(Base):
	"""
	Справочник типов оружия.
	Реализует требование ТЗ о хранении типа оружия (Simple, Martial и т.д.).
	"""
	__tablename__ = "weapon_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True)
	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Martial', 'Simple'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="weapon_types") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_weapon_types")
	weapons: Mapped[list["Weapon"]] = relationship("Weapon", back_populates="type_obj", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<WeaponType(id={self.id}, name='{self.name}')>"

# --- КЛАССЫ ОРУЖИЯ ---
class WeaponClass(Base):
	"""
	Конкретные классы оружия внутри типа (например, тип 'Martial' содержит классы 'Sword', 'Axe', 'Bow').
	Необходимо для реализации требований владения оружием у классов персонажей.
	"""
	__tablename__ = "weapon_classes"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(	PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True)
	type_id: Mapped[int] = mapped_column(Integer, ForeignKey("weapon_types.id", ondelete="CASCADE"), nullable=False, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. 'Sword', 'Bow'
	slug: Mapped[str] = mapped_column(String(50), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	system: Mapped["GameSystem"] = relationship("GameSystem")
	weapon_type: Mapped["WeaponType"] = relationship("WeaponType", backref="classes")
	weapons: Mapped[list["Weapon"]] = relationship("Weapon", back_populates="weapon_class", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<WeaponClass(id={self.id}, name='{self.name}', type_id={self.type_id})>"

# --- ДОСПЕХИ ---
class Armor(Base):
	"""
	Специфические параметры доспехов.
	Связаны один-к-одному с базовой таблицей equipment.
	"""
	__tablename__ = "armor"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	base_item_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
	armor_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("armor_types.id"), nullable=False, index=True)
	# Механика защиты
	base_armor_class: Mapped[int] = mapped_column(Integer, nullable=False) # Базовый КЗ без модификаторов
	requires_stealth_disadvantage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	strength_requirement: Mapped[int | None] = mapped_column(Integer, nullable=True) # Минимальная Сила
	is_heavy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	max_dex_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True) # Лимит бонуса Ловкости к КЗ
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	base_item: Mapped["Equipment"] = relationship("Equipment", back_populates="armor")
	type_obj: Mapped["ArmorType"] = relationship("ArmorType")

	def __repr__(self) -> str:
		return f"<Armor(id='{self.id}', name='{self.base_item.name}', AC={self.base_armor_class})>"

# --- ТИПЫ ДОСПЕХОВ ---
class ArmorType(Base):
	"""
	Справочник типов доспехов.
	Реализует требование ТЗ о хранении типа доспеха (Light, Medium, Heavy).
	"""
	__tablename__ = "armor_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True)
	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Heavy', 'Shield'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_shield: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="armor_types") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_armor_types")
	armor: Mapped[list["Armor"]] = relationship("Armor", back_populates="type_obj", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<ArmorType(id={self.id}, name='{self.name}', shield={self.is_shield})>"

# --- МАГИЧЕСКИЕ ПРЕДМЕТЫ ---
class MagicalItem(Base):
	"""
	Специфические параметры магических предметов.
	Наследует свойства базового снаряжения и добавляет уникальные эффекты.
	"""
	__tablename__ = "magical_items"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	base_item_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
	rarity_id: Mapped[int] = mapped_column(Integer, ForeignKey("rarities.id"), nullable=False, index=True)
	# Механика активации согласно ТЗ
	requires_attunement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	attunement_restriction: Mapped[str | None] = mapped_column(String(255), nullable=True)
	# e.g. 'Dwarf', 'Spellcaster', 'Chaotic Good'
	charges_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
	charges_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
	recharge_condition: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. 'dawn'
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	lore_description: Mapped[str | None] = mapped_column(Text, nullable=True) # История предмета
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	base_item: Mapped["Equipment"] = relationship("Equipment", back_populates="magical_items")
	rarity: Mapped["Rarity"] = relationship("Rarity", back_populates="magical_items")
	effects: Mapped[list["Effect"]] = relationship("Effect", secondary="item_effects", back_populates="magical_items", cascade="all, delete")

	def __repr__(self) -> str:
		return f"<MagicalItem(id='{self.id}', name='{self.base_item.name}', rarity={self.rarity.name})>"

# Ассоциативная таблица для связи Предметов и Эффектов (№19)
class ItemEffect(Base):
	__tablename__ = "item_effects"

	item_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("magical_items.id", ondelete="CASCADE"), primary_key=True)
	effect_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("effects.id", ondelete="CASCADE"), primary_key=True)

# --- АРТЕФАКТЫ ---
class Artifact(Base):
	"""
	Уникальные артефакты.
	Реализует требование ТЗ о хранении свойств артефактов как отдельного слоя поверх магических предметов.
	В отличие от обычных магических предметов, артефакты обычно нельзя уничтожить обычными средствами.
	"""
	__tablename__ = "artifacts"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	base_item_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
	rarity_id: Mapped[int] = mapped_column(Integer, ForeignKey("rarities.id"), nullable=False, index=True)
	# Механика разрушения/уничтожения согласно лору
	destruction_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
	# e.g. 'Бросить в жерло Роковой горы', 'Уничтожить только Молотом Дварфов'
	is_sentient: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	sentience_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"int": 16, "wis": 15, "cha": 18, "communication": "telepathy", "languages": ["common", "draconic"]}
	curses_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	requires_attunement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	lore_description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	base_item: Mapped["Equipment"] = relationship("Equipment", back_populates="artifacts")
	rarity: Mapped["Rarity"] = relationship("Rarity", back_populates="artifacts")
	properties: Mapped[list["ArtifactProperty"]] = relationship("ArtifactProperty", back_populates="artifact", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Artifact(id='{self.id}', name='{self.base_item.name}')>"

# --- СВОЙСТВА АРТЕФАКТОВ ---
class ArtifactProperty(Base):
	"""
	Специфические свойства артефактов (рандомизированные или фиксированные).
	Например: 'Random Property Table A', 'Minor Beneficial Property'.
	"""
	__tablename__ = "artifact_properties"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	artifact_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True)
	property_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. 'random_major', 'fixed_ability'
	payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}") # Данные свойства
	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	artifact: Mapped["Artifact"] = relationship("Artifact", back_populates="properties")

	def __repr__(self) -> str:
		return f"<ArtifactProperty(id='{self.id}', type='{self.property_type}')>"