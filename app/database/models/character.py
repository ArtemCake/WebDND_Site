# app/database/models/character.py

from Config.imports import (
	DateTime, func, UniqueConstraint,
	Integer, String, Text, Boolean, ForeignKey, SmallInteger,
	relationship, JSON, datetime, Mapped, mapped_column, backref)
from app.database.database import Base


class Character(Base):
	"""Персонажи игроков и NPC"""
	__tablename__ = "characters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	user_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)
	ruleset_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True
	)
	organization_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
	)

	race_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("races.id", ondelete="RESTRICT"), nullable=False, index=True
	)
	background_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("backgrounds.id", ondelete="RESTRICT"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	character_type: Mapped[str] = mapped_column(String(20), nullable=False, default="PC")
	alignment: Mapped[str] = mapped_column(String(20), default="Neutral")
	deity: Mapped[str | None] = mapped_column(String(100), nullable=True)
	portrait_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
	bio: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Хранилище сырых характеристик (для быстрого чтения фронтендом)
	stats_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	total_experience_points: Mapped[int] = mapped_column(Integer, default=0)
	proficiency_bonus: Mapped[int] = mapped_column(SmallInteger, default=2)

	# --- Связи ---
	user: Mapped["User | None"] = relationship("User", back_populates="characters")
	ruleset: Mapped["Ruleset | None"] = relationship("Ruleset", back_populates="characters")
	organization: Mapped["Organization | None"] = relationship("Organization", back_populates="members")

	race: Mapped["Race"] = relationship("Race")
	background: Mapped["Background | None"] = relationship("Background")

	level_history: Mapped[list["CharacterLevel"]] = relationship(
		"CharacterLevel",
		back_populates="character",
		cascade="all, delete-orphan",
		order_by="CharacterLevel.level_number",
		passive_deletes=True
	)

	spell_slots: Mapped[list["SpellSlot"]] = relationship(
		"SpellSlot",
		back_populates="character",
		cascade="all, delete-orphan",
		lazy="selectin"
	)

	abilities_detail: Mapped[list["CharacterAbilityValue"]] = relationship(
		"CharacterAbilityValue",
		back_populates="character",
		cascade="all, delete-orphan",
		lazy="joined"
	)

	skills_detail: Mapped[list["SkillProficiency"]] = relationship(
		"SkillProficiency",
		back_populates="character",
		cascade="all, delete-orphan",
		lazy="joined"
	)

	saving_throws: Mapped[list["SavingThrow"]] = relationship(
		"SavingThrow",
		back_populates="character",
		cascade="all, delete-orphan",
		lazy="joined"
	)

	feats: Mapped[list["Feat"]] = relationship(
		secondary="character_feats",
		backref=backref("holders", lazy="dynamic"),
		lazy="selectin"
	)

	languages: Mapped[list["Language"]] = relationship(
		secondary="character_languages",
		backref=backref("speakers", lazy="dynamic"),
		lazy="selectin"
	)

	equipment: Mapped[list["Equipment"]] = relationship(
		"Equipment",
		back_populates="character",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	controlled_allies: Mapped[list["Character"]] = relationship(
		"Character",
		secondary="character_allies",
		primaryjoin=(id == "character_allies.c.owner_character_id"),
		secondaryjoin=(id == "character_allies.c.ally_character_id"),
		backref=backref("controller", lazy="dynamic"),
		lazy="selectin"
	)

	conditions: Mapped[list["Condition"]] = relationship(
		secondary="character_conditions",
		backref=backref("active_conditions", lazy="dynamic"),
		lazy="selectin"
	)

	@property
	def current_level(self) -> int:
		if not self.level_history:
			return 0
		return max(level.level_number for level in self.level_history)

	def __repr__(self) -> str:
		return f"<Character(id={self.id}, name='{self.name}', lvl={self.current_level})>"

# --- Вспомогательные таблицы связей М2М и детальные модели ---

class CharacterAbilityValue(Base):
	"""
	Конкретное значение характеристики у персонажа с учетом бонусов от предметов/заклинаний.
	Использует справочник ability_types для поддержки кастомных статов (Мана, Удача).
	"""
	__tablename__ = "character_abilities"

	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
	)
	ability_type_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("ability_types.id", ondelete="CASCADE"), primary_key=True
	)
	score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=8)

	character: Mapped["Character"] = relationship(back_populates="abilities_detail")
	type: Mapped["AbilityType"] = relationship()

	__table_args__ = (
		UniqueConstraint('character_id', 'ability_type_id', name='uq_char_ability_val'),
	)

	def __repr__(self) -> str:
		return f"<CharAbility(char={self.character_id}, abil='{self.type.name}', val={self.score})>"

class SkillProficiency(Base):
	"""
	Владение навыком или инструментом персонажем.
	Объединяет классические навыки (Skills) и инструменты (Tools/Vehicles).
	"""
	__tablename__ = "skill_proficiencies"

	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
	)
	skill_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
	)

	proficiency_category: Mapped[str] = mapped_column(
		String(20), nullable=False, default='skill', server_default='skill'
	)
	is_expertise: Mapped[bool] = mapped_column(Boolean(), default=False)
	proficient: Mapped[bool] = mapped_column(Boolean(), default=True)

	character: Mapped["Character"] = relationship(back_populates="skills_detail")
	skill: Mapped["Skill"] = relationship()

	__table_args__ = (
		UniqueConstraint('character_id', 'skill_id', name='uq_char_skill_prof'),
	)

	def __repr__(self) -> str:
		status = "Expert" if self.is_expertise else ("Yes" if self.proficient else "No")
		return f"<SkillProf(char={self.character_id}, skill='{self.skill.name}', prof={status})>"

class SavingThrow(Base):
	"""
	Спасброски персонажа: владение + бонусы.
	"""
	__tablename__ = "saving_throws"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
	)
	ability_type_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("ability_types.id", ondelete="CASCADE"), nullable=False
	)
	is_proficient: Mapped[bool] = mapped_column(Boolean(), default=False)
	bonus_override: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)

	character: Mapped["Character"] = relationship(back_populates="saving_throws")
	ability_type: Mapped["AbilityType"] = relationship()

	__table_args__ = (
		UniqueConstraint('character_id', 'ability_type_id', name='uq_char_save'),
	)

	def __repr__(self) -> str:
		prof = "Prof" if self.is_proficient else "NoProf"
		return f"<SavingThrow(char={self.character_id}, abil='{self.ability_type.abbreviation}', {prof})>"

class SpellSlot(Base):
	"""
	Доступные ячейки заклинаний конкретного персонажа.
	Хранит текущее состояние ресурсов мага после отдыха.
	"""
	__tablename__ = "spell_slots"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey('characters.id', ondelete="CASCADE"), nullable=False, index=True
	)
	spell_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
	slots_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
	slots_used: Mapped[int] = mapped_column(SmallInteger, default=0)

	character: Mapped["Character"] = relationship(back_populates="spell_slots")

	__table_args__ = (
		UniqueConstraint('character_id', 'spell_level', name='uq_char_spell_slot'),
	)

	def __repr__(self) -> str:
		return f"<SpellSlot(char={self.character_id}, lvl={self.spell_level}, used={self.slots_used}/{self.slots_total})>"

class CharacterLevel(Base):
	"""
	История уровней персонажа. Решает проблему пересчета HP при изменении прошлых уровней.
	"""
	__tablename__ = "character_levels"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey('characters.id', ondelete="CASCADE"), nullable=False, index=True
	)
	class_id: Mapped[int] = mapped_column(Integer, ForeignKey('classes.id'), nullable=False, index=True)
	subclass_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('subclasses.id'), nullable=True, index=True)

	level_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
	experience_at_level: Mapped[int] = mapped_column(Integer, nullable=False)

	hit_dice_collected_json: Mapped[dict] = mapped_column(JSON, nullable=False)
	features_unlocked_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	character: Mapped["Character"] = relationship(back_populates="level_history")
	dnd_class: Mapped["Class_"] = relationship("Class_")
	subclass: Mapped["Subclass | None"] = relationship("Subclass")

	__table_args__ = (
		UniqueConstraint('character_id', 'level_number', name='uq_character_level_num'),
	)

	def __repr__(self) -> str:
		sub_name = f", {self.subclass.name}" if self.subclass else ""
		return f"<CharLvl(char={self.character_id}, cls={self.dnd_class.name}{sub_name}, lvl={self.level_number})>"