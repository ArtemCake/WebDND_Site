# app/database/models/core_game_models.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey,
	relationship, datetime, DateTime, func, Mapped, mapped_column)
from app.database.database import Base

# --- СВЯЗУЮЩИЕ МОДЕЛИ ---

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

# --- Основные МОДЕЛИ ---

class Race(Base):
	"""
	Справочник рас. Поддерживает хоумбрю-правила через поле homebrew_rules.
	"""
	__tablename__ = "races"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Режим работы таблицы
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)

	# Кастомные бонусы к характеристикам, скорости или темному зрению от Мастера
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	characters: Mapped[list["Character"]] = relationship(back_populates="race")
	traits: Mapped[list["Trait"]] = relationship("Trait", back_populates="race", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Race(id={self.id}, name='{self.name}', status={status})>"

class Class(Base):
	"""
	Справочник классов. Поддерживает создание подклассов (Subclass).
	"""
	__tablename__ = "classes"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
	hit_die: Mapped[int] = mapped_column(Integer, nullable=False, default=8) # d8, d10 и т.д.
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	characters: Mapped[list["CharacterClassLink"]] = relationship(back_populates="base_class")
	subclasses: Mapped[list["Subclass"]] = relationship("Subclass", back_populates="parent_class", cascade="all, delete-orphan")

	# Связь на связующую таблицу, чтобы иметь доступ к available_at_level
	class_spells: Mapped[list["ClassSpellLink"]] = relationship(
		back_populates="base_class",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	# Прямой список заклинаний (только чтение, без управления через эту связь)
	spells: Mapped[list["Spell"]] = relationship(
		secondary="class_spells",
		viewonly=True,
		uselist=True,
		back_populates="classes"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Class(id={self.id}, name='{self.name}', HD=d{self.hit_die}, status={status})>"

class Subclass(Base):
	"""
	Подкласс (Архетип). Пример: Школа Эвокации для Волшебника.
	"""
	__tablename__ = "subclasses"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	parent_class_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("classes.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	parent_class: Mapped["Class"] = relationship(back_populates="subclasses")

	def __repr__(self) -> str:
		return f"<Subclass(id={self.id}, name='{self.name}', class_id={self.parent_class_id})>"

class Background(Base):
	"""
	Предыстория персонажа. Дает навыки и владение инструментами.
	"""
	__tablename__ = "backgrounds"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	characters: Mapped[list["Character"]] = relationship(back_populates="background")
	skills: Mapped[list["Skill"]] = relationship("Skill", secondary="background_skills", back_populates="backgrounds")

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Background(id={self.id}, name='{self.name}', status={status})>"

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
		back_populates="character",
		cascade="all, delete-orphan"
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
		back_populates="character", # <-- ОНА ССЫЛАЕТСЯ НА "CHARACTER"
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	ability_scores: Mapped[list["CharacterAbilityValue"]] = relationship(
		back_populates="character",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	def __repr__(self) -> str:
		classes_str = ", ".join([f"{link.base_class.name} {link.level}" for link in self.class_links])
		return f"<Character(id={self.id}, name='{self.name}', LvL={self.level}, Classes=[{classes_str}])>"

class Ruleset(Base):
	"""
	Набор правил (Ruleset) для конкретной кампании.
	Позволяет переопределять механики SRD без изменения кода.
	"""
	__tablename__ = "rulesets"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	campaign_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	owner_id: Mapped[int | None] = mapped_column(  # <-- ДОБАВИТЬ
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False) # Например: "My Homebrew D&D 5e"
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Переопределение базовых формул (примеры)
	death_save_success_dc: Mapped[int] = mapped_column(Integer, default=10)
	short_rest_dice_count: Mapped[int] = mapped_column(Integer, default=0) # Сколько кубиков восстанавливается

	# Кастомные бонусы к спасброскам или скиллам на уровне всей кампании
	global_modifiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	campaign: Mapped["Campaign"] = relationship(back_populates="ruleset")

	owner: Mapped["User | None"] = relationship(
		back_populates="rules_created",
		foreign_keys=[owner_id]
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Ruleset(id={self.id}, name='{self.name}', status={status})>"

class HomebrewEntity(Base):
	"""
	Универсальная сущность для любого домашнего контента
	(Расы, Заклинания, Монстры, Магические предметы).
	"""
	__tablename__ = "homebrew_entities"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)

	owner_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	# Полиморфная привязка к типу сущности
	entity_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'spell', 'race', 'item'

	name: Mapped[str] = mapped_column(String(150), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # Весь объект заклинания/предмета целиком

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


	owner: Mapped["User | None"] = relationship(back_populates="homebrew_entities")