# app/database/models/references.py

from Config.imports import (
	DateTime, func,Integer, String, Text, Boolean, ForeignKey, Float,
	relationship, JSON, datetime, Mapped, mapped_column)
from app.database.database import Base


# ---------------------------------------------------------------------------
# AbilityType — типы характеристик (6 базовых + кастомные: Мана, Удача, Честь)
# ---------------------------------------------------------------------------

class AbilityType(Base):
	"""
	Справочник типов характеристик.
	Базовые: Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma.
	Кастомные: Luck, Mana, Honor и т.д. (is_custom=True).
	"""
	__tablename__ = "ability_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(
		String(50), nullable=False, unique=True,
		comment="Полное название: Strength, Dexterity, Luck, Mana"
	)
	abbreviation: Mapped[str] = mapped_column(
		String(3), nullable=False, unique=True,
		comment="Краткое обозначение: STR, DEX, LCK, MAN"
	)
	is_custom: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="True, если характеристика добавлена пользователем, а не из SRD"
	)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self) -> str:
		return f"<AbilityType(id={self.id}, name='{self.name}', abbr='{self.abbreviation}')>"

# ---------------------------------------------------------------------------
# Skill — навыки и инструменты (18 базовых + кастомные)
# ---------------------------------------------------------------------------

class Skill(Base):
	"""
	Справочник навыков, инструментов и транспортных средств.
	Категории: 'skill' (Stealth, Arcana…), 'tool' (Thieves' Tools…), 'vehicle' (Land Vehicles…).
	"""
	__tablename__ = "skills"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(
		String(100), nullable=False, unique=True,
		comment="Название: Stealth, Arcana, Thieves' Tools, Land Vehicles"
	)
	slug: Mapped[str] = mapped_column(
		String(100), nullable=False, unique=True, index=True
	)
	linked_ability_abbr: Mapped[str | None] = mapped_column(
		String(3), nullable=True,
		comment="Сокращение характеристики, от которой зависит навык (DEX, INT…). "
		        "Связь через строку, а не FK — быстрее читается и не требует JOIN."
	)
	skill_category: Mapped[str] = mapped_column(
		String(20), nullable=False, default='skill',
		comment="Тип: 'skill', 'tool', 'vehicle'"
	)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_custom: Mapped[bool] = mapped_column(Boolean(), default=False)

	def __repr__(self) -> str:
		return f"<Skill(id={self.id}, name='{self.name}', abil='{self.linked_ability_abbr}')>"

# ---------------------------------------------------------------------------
# Feat — черты (Alert, Lucky, Great Weapon Master…)
# ---------------------------------------------------------------------------

class Feat(Base):
	"""
	Черты персонажей. Могут быть официальными (is_homebrew=False)
	или созданными пользователем (is_homebrew=True).
	"""
	__tablename__ = "feats"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	prerequisite_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Требования: {'min_level': 4, 'ability': 'STR', 'min_score': 13}"
	)
	bonus_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Бонусы: {'ability_increase': {'STR': 1}, 'features': ['...']}"
	)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	is_homebrew: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="True, если черта не из официальных книг"
	)

	def __repr__(self) -> str:
		return f"<Feat(id={self.id}, name='{self.name}')>"

# ---------------------------------------------------------------------------
# Language — языки (Common, Elvish, Draconic, Thieves' Cant…)
# ---------------------------------------------------------------------------

class Language(Base):
	"""
	Языки, доступные персонажам и расам.
	"""
	__tablename__ = "languages"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	script: Mapped[str | None] = mapped_column(
		String(50), nullable=True,
		comment="Письменность: Elvish, Draconic, Dwarvish…"
	)
	is_exotic: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="Экзотические языки требуют отдельного обучения"
	)
	is_secret: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="Тайные языки (Thieves' Cant, Druidic)"
	)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self) -> str:
		return f"<Language(id={self.id}, name='{self.name}')>"

# ---------------------------------------------------------------------------
# Condition — состояния (Blinded, Charmed, Poisoned…)
# ---------------------------------------------------------------------------

class Condition(Base):
	"""
	Состояния персонажа. Могут быть кастомными (is_custom=True).
	"""
	__tablename__ = "conditions"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	effects_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Механики: {'disadvantage_on': ['attack_rolls'], 'speed': 0, …}"
	)
	is_custom: Mapped[bool] = mapped_column(Boolean(), default=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self) -> str:
		return f"<Condition(id={self.id}, name='{self.name}')>"

# ---------------------------------------------------------------------------
# Organization — организации и фракции
# ---------------------------------------------------------------------------

class Organization(Base):
	"""
	Организации, гильдии, фракции мира.
	Связываются с персонажами через Character.organization_id.
	"""
	__tablename__ = "organizations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	alignment: Mapped[str | None] = mapped_column(
		String(20), nullable=True,
		comment="Мировоззрение организации: Lawful Good, Chaotic Evil…"
	)
	leader_character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True,
		comment="Текущий лидер (персонаж)"
	)
	is_secret: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="Тайная организация (игроки могут не знать о ней)"
	)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- Связи ---
	leader: Mapped["Character | None"] = relationship(
		"Character", foreign_keys=[leader_character_id]
	)
	members: Mapped[list["Character"]] = relationship(
		"Character",
		back_populates="organization",
		foreign_keys="Character.organization_id",
	)

	def __repr__(self) -> str:
		return f"<Organization(id={self.id}, name='{self.name}')>"

# ---------------------------------------------------------------------------
# ShopVendor — магазины и торговцы
# ---------------------------------------------------------------------------

class ShopVendor(Base):
	"""
	Магазины, лавки, странствующие караваны.
	Инвентарь хранится через M2M-таблицу shop_inventory (см. associations.py).
	"""
	__tablename__ = "shops"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	owner_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
	)
	location_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True,
	)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	shop_type: Mapped[str] = mapped_column(
		String(50), nullable=False,
		comment="Тип: general, magic, weapons, armor, potions, scrolls"
	)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	buy_markup_multiplier: Mapped[float] = mapped_column(
		Float, default=1.0,
		comment="Наценка при покупке игроком (1.0 = базовая цена)"
	)
	sell_discount_multiplier: Mapped[float] = mapped_column(
		Float, default=0.5,
		comment="Коэффициент при продаже игроком (0.5 = 50% цены)"
	)
	is_traveling: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="Странствующий торговец (может появляться в разных локациях)"
	)
	restock_frequency: Mapped[str] = mapped_column(
		String(20), default='session',
		comment="Частота обновления ассортимента: session, day, week, never"
	)
	gold_reserve: Mapped[int] = mapped_column(
		Integer, default=0,
		comment="Резерв золота торговца для выкупа предметов у игроков (в GP)"
	)

	# --- Связи ---
	owner: Mapped["User | None"] = relationship("User")
	location: Mapped["Location | None"] = relationship("Location")

	def __repr__(self) -> str:
		return f"<ShopVendor(id={self.id}, name='{self.name}', type='{self.shop_type}')>"