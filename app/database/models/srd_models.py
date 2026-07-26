# app/database/models/srd_models.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey,
	relationship, Mapped, mapped_column)
from app.database.database import Base


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
		back_populates="damage_type",
		cascade="all, delete-orphan"
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

	# Значение сопротивления.
	# -1 (Иммунитет), 0.5 (Сопротивление), 2 (Уязвимость), 1 (Обычный урон)
	modifier: Mapped[float] = mapped_column(default=0.5, nullable=False)

	notes: Mapped[str | None] = mapped_column(String(200), nullable=True) # Источник: Расовая черта, Кольцо защиты...

	character: Mapped["Character"] = relationship(back_populates="resistances")
	damage_type: Mapped["DamageType"] = relationship(back_populates="resistances")

	def __repr__(self) -> str:
		mod_map = {-1: "Immune", 0.5: "Resistant", 2: "Vulnerable"}
		return f"<Resistance(char={self.character_id}, dmg={self.damage_type.name}, mod={mod_map.get(self.modifier, 'Custom')})>"

class AbilityScore(Base):
	"""
	Справочник характеристик (STR, DEX, CON...).
	Позволяет расширять список за пределы стандартных 6 атрибутов.
	"""
	__tablename__ = "ability_scores"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True) # strength, dexterity
	short_name: Mapped[str] = mapped_column(String(3), nullable=False, unique=True) # STR, DEX

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	values: Mapped[list["CharacterAbilityValue"]] = relationship(
		back_populates="ability_score",
		cascade="all, delete-orphan"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<AbilityScore(id={self.id}, name='{self.short_name}', status={status})>"

class CharacterAbilityValue(Base):
	"""
	Конкретное значение характеристики для конкретного персонажа.
	Разделено от справочника, чтобы хранить бонусы мастерства или временные изменения.
	"""
	__tablename__ = "character_ability_values"

	character_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("characters.id", ondelete="CASCADE"),
		primary_key=True
	)
	ability_score_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("abilities.id", ondelete="RESTRICT"), # См. примечание ниже
		primary_key=True
	)

	score: Mapped[int] = mapped_column(Integer, nullable=False) # Базовое значение (обычно 3..20)
	bonus: Mapped[int] = mapped_column(Integer, nullable=False) # Модификатор (округленный floor((score-10)/2))

	proficient: Mapped[bool] = mapped_column(Boolean(), default=False) # Есть ли владение спасброском?
	save_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True) # Бонус спасброска (если профайент)

	character: Mapped["Character"] = relationship(back_populates="ability_scores")
	ability_definition: Mapped["AbilityDefinition"] = relationship()

	def __repr__(self) -> str:
		return f"<CharAbility(char={self.character_id}, abil='{self.ability_definition.short_name}', val={self.score})>"

class AbilityDefinition(Base):
	"""
	Справочник самих названий характеристик (STR, DEX...).
	Вынесен отдельно, чтобы Мастер мог создать свою систему статов.
	"""
	__tablename__ = "abilities"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	short_name: Mapped[str] = mapped_column(String(3), nullable=False, unique=True) # STR, INT
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)

	scores: Mapped[list[CharacterAbilityValue]] = relationship(back_populates="ability_definition")

	def __repr__(self) -> str:
		return f"<AbilityDef(id={self.id}, name='{self.name}')>"