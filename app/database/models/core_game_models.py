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
	spells: Mapped[list["Spell"]] = relationship("Spell", secondary="class_spells", back_populates="classes")

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
		foreign_keys=user_id, # Явно указываем FK
		lazy="selectin" # Оптимизация загрузки
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

	def __repr__(self) -> str:
		classes_str = ", ".join([f"{link.base_class.name} {link.level}" for link in self.class_links])
		return f"<Character(id={self.id}, name='{self.name}', LvL={self.level}, Classes=[{classes_str}])>"