# app/database/models/srd_models.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey,  DateTime, func,
	relationship, Mapped, mapped_column, datetime, Table, Column)
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