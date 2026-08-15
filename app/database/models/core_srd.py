# app/database/models/core_srd.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey,  DateTime, func, text,
	relationship, Mapped, mapped_column, datetime, Table, Column, Float, Index)
from app.database.database import Base


character_traits = Table(
	'character_traits', Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('trait_id', Integer, ForeignKey('traits.id', ondelete="CASCADE"), primary_key=True)
)

race_traits = Table(
	'race_traits', Base.metadata,
	Column('race_id', Integer, ForeignKey('races.id', ondelete="CASCADE"), primary_key=True),
	Column('trait_id', Integer, ForeignKey('traits.id', ondelete="CASCADE"), primary_key=True)
)

class_spills = Table(
	'class_skills', Base.metadata,
	Column('class_id', Integer, ForeignKey('classes.id', ondelete="CASCADE"), primary_key=True),
	Column('skill_id', Integer, ForeignKey('skills.id', ondelete="CASCADE"), primary_key=True)
)

skill_ability_links = Table(
	'skill_ability_links', Base.metadata,
	Column('skill_id', Integer, ForeignKey('skills.id', ondelete="CASCADE"), primary_key=True),
	Column('ability_score_id', Integer, ForeignKey('ability_scores.id', ondelete="CASCADE"), primary_key=True),
	Column('base_value', Integer, nullable=False) # Базовый бонус навыка от характеристики (обычно совпадает с кратностью характеристики)
)

spell_damage_types = Table(
	'spell_damage_types', Base.metadata,
	Column('spell_id', Integer, ForeignKey('spells.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True)
)

spell_classes = Table(
	'spell_classes', Base.metadata,
	Column('spell_id', Integer, ForeignKey('spells.id', ondelete="CASCADE"), primary_key=True),
	Column('class_id', Integer, ForeignKey('classes.id', ondelete="CASCADE"), primary_key=True)
)

background_skills = Table(
	'background_skills', Base.metadata,
	Column('background_id', Integer, ForeignKey('backgrounds.id', ondelete="CASCADE"), primary_key=True),
	Column('skill_id', Integer, ForeignKey('skills.id', ondelete="CASCADE"), primary_key=True)
)

# Связующая таблица Класс <-> Заклинание (какие заклы доступны классу по умолчанию)
class ClassSpellLink(Base):
	__tablename__ = "class_spells"

	class_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("classes.id", ondelete="CASCADE"),
		primary_key=True
	)
	spell_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("spells.id", ondelete="CASCADE"),
		primary_key=True
	)

	available_at_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

	base_class: Mapped["Class"] = relationship(
		"Class",
		back_populates="class_spells",
		overlaps="spell"
	)

	spell: Mapped["Spell"] = relationship(
		"Spell",
		back_populates="class_links",  # Исправлено с "spells" на "class_links"
		overlaps="base_class"
	)

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
		uselist=True,
		back_populates="classes",
		overlaps="base_class,spell_links, class_spells"
	)

	skills: Mapped[list["Skill"]] = relationship(
		secondary="class_skills",
		back_populates="classes",
		lazy="selectin"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Class(id={self.id}, name='{self.name}', HD=d{self.hit_die}, status={status})>"

class Spell(Base):
	"""
	Базовый справочник заклинаний (SRD или Homebrew).
	"""
	__tablename__ = "spells"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	level: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 0 для заговоров (cantrips)
	school: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # Evocation, Necromancy и т.д.

	casting_time: Mapped[str] = mapped_column(String(100), nullable=False)
	range_: Mapped[str] = mapped_column("range", String(100), nullable=False)
	components: Mapped[str] = mapped_column(Text, nullable=False) # V, S, M (xxx gp)
	duration: Mapped[str] = mapped_column(String(100), nullable=False)

	description: Mapped[str] = mapped_column(Text, nullable=False)
	higher_levels: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_ritual: Mapped[bool] = mapped_column(Boolean(), default=False)
	concentration: Mapped[bool] = mapped_column(Boolean(), default=False)

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	classes: Mapped[list["Class"]] = relationship(
		secondary="class_spells",
		back_populates="spells",
		overlaps="spell_links,base_class,class_spells,spell"
	)

	class_links: Mapped[list["ClassSpellLink"]] = relationship(
		back_populates="spell",
		cascade="all, delete-orphan",
		passive_deletes=True,
		lazy="selectin",
		overlaps="classes,spell"
	)

	character_spells: Mapped[list["CharacterSpell"]] = relationship(
		back_populates="spell",
		cascade="all, delete-orphan",
		passive_deletes=True,
		lazy="selectin"
	)

	damage_types: Mapped[list["DamageType"]] = relationship(
		secondary="spell_damage_types",
		back_populates="spells",
		lazy="selectin"
	)

	__table_args__ = (
		Index('ix_spells_name_lower', text("lower(name)")),
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Spell(id={self.id}, name='{self.name}', LvL={self.level}, status={status})>"

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

class Monster(Base):
	"""
	Справочник монстров (Бестиарий).
	Служит шаблоном для создания Токенов на карте во время боя.
	"""
	__tablename__ = "monsters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	# Владение сущностью
	creator_id: Mapped[int | None] = mapped_column(
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
	size: Mapped[str] = mapped_column(String(20), default="Medium") # Tiny, Small, Medium, Large...
	type_: Mapped[str] = mapped_column("type", String(50), nullable=False, index=True) # Humanoid, Undead, Dragon...

	alignment: Mapped[str | None] = mapped_column(String(20), nullable=True)
	armor_class: Mapped[int] = mapped_column(Integer, nullable=False)
	hit_points: Mapped[int] = mapped_column(Integer, nullable=False)
	speed: Mapped[int] = mapped_column(Integer, default=30)

	ability_scores: Mapped[dict] = mapped_column(JSONB, nullable=False) # {"str": 10, "dex": 14, ...}

	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	actions: Mapped[str | None] = mapped_column(Text, nullable=True) # Описание действий в JSON или Markdown

	challenge_rating: Mapped[float] = mapped_column(Float(), default=0.125) # CR 0, 1/8, 1/4... 30

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	creator: Mapped["User | None"] = relationship()

	tokens: Mapped[list["Token"]] = relationship(
		back_populates="monster",
		primaryjoin="Monster.id == Token.monster_id",
		cascade="all, delete-orphan",
		lazy="selectin"
	)

	campaign: Mapped["Campaign | None"] = relationship(
		back_populates="monsters",
		foreign_keys=[campaign_id],
		lazy="selectin"
	)

	combat_encounters: Mapped[list["Encounter"]] = relationship(
		secondary="encounter_monsters",
		back_populates="monsters",
		lazy="selectin" # Оптимизация загрузки
	)

	def __repr__(self) -> str:
		return f"<Monster(id={self.id}, name='{self.name}', CR={self.challenge_rating})>"

class DamageType(Base):
	"""
	Справочник типов урона (Огонь, Холод, Рубящий и т.д.).
	Используется для проверки Устойчивости/Уязвимости цели.
	"""
	__tablename__ = "damage_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	srd_reference: Mapped[str | None] = mapped_column(String(200), nullable=True) # Ссылка на страницу Basic Rules

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	spells: Mapped[list["Spell"]] = relationship(
		secondary="spell_damage_types",
		back_populates="damage_types"
	)

	resistances: Mapped[list["Resistance"]] = relationship(back_populates="damage_type")

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<DamageType(id={self.id}, name='{self.name}', status={status})>"

class Resistance(Base):
	"""
	Связующая сущность между Персонажем/Расой и Типом урона.
	Хранит модификатор защиты (например, Сопротивление = *0.5 урона).
	"""
	__tablename__ = "resistances"

	character_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("characters.id", ondelete="CASCADE"),
		primary_key=True
	)
	damage_type_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("damage_types.id", ondelete="CASCADE"),
		primary_key=True
	)

	character: Mapped["Character"] = relationship(
		back_populates="resistances",
		foreign_keys=[character_id]
	)

	# Значение сопротивления.
	# -1 (Иммунитет), 0.5 (Сопротивление), 2 (Уязвимость), 1 (Обычный урон)
	modifier: Mapped[float] = mapped_column(default=0.5, nullable=False)

	notes: Mapped[str | None] = mapped_column(String(200), nullable=True) # Источник: Расовая черта, Кольцо защиты...

	damage_type: Mapped["DamageType"] = relationship(back_populates="resistances")

	def __repr__(self) -> str:
		mod_map = {-1: "Immune", 0.5: "Resistant", 2: "Vulnerable"}
		return f"<Resistance(char={self.character_id}, dmg={self.damage_type.name}, mod={mod_map.get(self.modifier, 'Custom')})>"

class AbilityScore(Base):
	__tablename__ = "ability_scores"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
	short_name: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	# Одна связь, которая ссылается на CharacterAbilityValue
	values: Mapped[list["CharacterAbilityValue"]] = relationship(
		back_populates="ability_score",
		cascade="all, delete-orphan"
	)

	skills: Mapped[list["Skill"]] = relationship(
		back_populates="ability_score",
		lazy="selectin"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<AbilityScore(id={self.id}, name='{self.short_name}', status={status})>"

class CharacterAbilityValue(Base):
	__tablename__ = "character_ability_values"

	character_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("characters.id", ondelete="CASCADE"),
		primary_key=True
	)
	ability_score_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("ability_scores.id", ondelete="RESTRICT"),
		primary_key=True
	)

	# Имя должно точно совпадать с back_populates в AbilityScore.values
	ability_score: Mapped["AbilityScore"] = relationship(
		back_populates="values",
		foreign_keys=[ability_score_id]
	)

	score: Mapped[int] = mapped_column(Integer, nullable=False)
	bonus: Mapped[int] = mapped_column(Integer, nullable=False)

	proficient: Mapped[bool] = mapped_column(Boolean(), default=False)
	save_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)

	character: Mapped["Character"] = relationship(back_populates="ability_scores")

	def __repr__(self) -> str:
		return f"<CharAbility(char={self.character_id}, abil='{self.ability_score.short_name}', val={self.score})>"

class Trait(Base):
	"""
	Справочник черт (Feats/Traits).
	Пример: Tough, Lucky, Actor, Sharpshooter.
	Может быть как официальным (SRD), так и хоумбрю-правилом Мастера.
	"""
	__tablename__ = "traits"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Механика SRD
	prerequisite: Mapped[str | None] = mapped_column(String(200), nullable=True) # Например: "Str 13 or Dex 13"
	is_bonus_action: Mapped[bool] = mapped_column(Boolean(), default=False)
	requires_attunement: Mapped[bool] = mapped_column(Boolean(), default=False)

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	characters: Mapped[list["Character"]] = relationship(
		secondary="character_traits",
		back_populates="traits",
		lazy="selectin"
	)

	races: Mapped[list["Race"]] = relationship(
		secondary="race_traits",
		back_populates="traits"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Trait(id={self.id}, name='{self.name}', status={status})>"

class Skill(Base):
	"""
	Справочник навыков (Skills).
	Пример: Acrobatics, Stealth, Perception, Athletics.
	Каждый навык привязан к одной из 6 базовых характеристик.
	"""
	__tablename__ = "skills"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

	# К какой характеристике относится навык (S, D, C, I, W, Ch)
	ability_score_short_name: Mapped[str] = mapped_column(
		String(3),
		ForeignKey("ability_scores.short_name", ondelete="RESTRICT"),
		nullable=False,
		index=True
	)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	# Обратная ссылка на характеристику (Strength, Dexterity...)
	ability_score: Mapped["AbilityScore"] = relationship(back_populates="skills")


	backgrounds: Mapped[list["Background"]] = relationship(
		secondary="background_skills",
		back_populates="skills"
	)

	classes: Mapped[list["Class"]] = relationship(
		secondary="class_skills",
		back_populates="skills",
		lazy="selectin"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Skill(id={self.id}, name='{self.name}', Abil={self.ability_score_short_name}, status={status})>"

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

	traits: Mapped[list["Trait"]] = relationship(
		secondary="race_traits",
		back_populates="races"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Race(id={self.id}, name='{self.name}', status={status})>"

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