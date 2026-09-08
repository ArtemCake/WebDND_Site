# backend/app/models/content/game_systems.py

"""Модели игровых систем (D&D, Pathfinder и др.) и домашних правил."""

from Config.imports import (String, Text, Boolean, DateTime, ForeignKey, PG_UUID,
	Mapped, mapped_column, relationship, JSONB, text, datetime, uuid4)
from backend.app.database.database import Base


class GameSystem(Base):
	"""
	Справочник игровых систем. Является корневым контейнером для всего контента.
	Например: 'DnD_5e', 'DnD_2024', 'Pathfinder_2e'.
	"""
	__tablename__ = "game_systems"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # Отображаемое имя
	slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)   # Для URL (dnd-5e)

	# Версия движка расчетов (для инвалидации кеша характеристик при обновлении системы)
	rules_engine_version: Mapped[str] = mapped_column(String(20), nullable=False, server_default="1.0")

	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	# Связи с контентом
	races: Mapped[list["Race"]] = relationship("Race", back_populates="system", cascade="all, delete-orphan")
	classes: Mapped[list["CharacterClass"]] = relationship("CharacterClass", back_populates="system", cascade="all, delete-orphan")
	spells: Mapped[list["Spell"]] = relationship("Spell", back_populates="system", cascade="all, delete-orphan")
	homebrew_rules: Mapped[list["HomebrewRule"]] = relationship("HomebrewRule", back_populates="system", cascade="all, delete-orphan")
	backgrounds: Mapped[list["Background"]] = relationship("Background", back_populates="system", cascade="all, delete-orphan")
	spell_levels: Mapped[list["SpellSlot"]] = relationship("SpellSlot", back_populates="system", cascade="all, delete-orphan")
	magic_schools: Mapped[list["MagicSchool"]] = relationship("MagicSchool", back_populates="system", cascade="all, delete-orphan")
	abilities: Mapped[list["Ability"]] = relationship("Ability", back_populates="system", cascade="all, delete-orphan")
	effects: Mapped[list["Effect"]] = relationship("Effect", back_populates="system", cascade="all, delete-orphan")
	damage_types: Mapped[list["DamageType"]] = relationship("DamageType", back_populates="system", cascade="all, delete-orphan")
	skills: Mapped[list["Skill"]] = relationship("Skill", back_populates="system", cascade="all, delete-orphan")
	characteristics: Mapped[list["Characteristic"]] = relationship("Characteristic", back_populates="system", cascade="all, delete-orphan")
	item_types: Mapped[list["ItemType"]] = relationship("ItemType", back_populates="system", cascade="all, delete-orphan")
	rarities: Mapped[list["Rarity"]] = relationship("Rarity", back_populates="system", cascade="all, delete-orphan")
	weapon_types: Mapped[list["WeaponType"]] = relationship("WeaponType", back_populates="system", cascade="all, delete-orphan")
	armor_types: Mapped[list["ArmorType"]] = relationship("ArmorType", back_populates="system", cascade="all, delete-orphan")
	creature_sizes: Mapped[list["CreatureSize"]] = relationship("CreatureSize", back_populates="system", cascade="all, delete-orphan")
	creature_types: Mapped[list["CreatureType"]] = relationship("CreatureType", back_populates="system", cascade="all, delete-orphan")
	languages: Mapped[list["Language"]] = relationship("Language", back_populates="system", cascade="all, delete-orphan")
	lore: Mapped[list["LoreEntry"]] = relationship("LoreEntry", back_populates="system", cascade="all, delete-orphan")
	npc_types: Mapped[list["NPCTag"]] = relationship("NPCTag", back_populates="system", cascade="all, delete-orphan")
	bestiary: Mapped[list["Creature"]] = relationship("Creature", back_populates="system", cascade="all, delete-orphan")
	feats: Mapped[list["Feat"]] = relationship( "Feat", back_populates="system", cascade="all, delete-orphan", lazy="selectin" )
	origins: Mapped[list["Origin"]] = relationship( "Origin", back_populates="system", cascade="all, delete-orphan", lazy="selectin" )

	def __repr__(self) -> str:
		return f"<GameSystem(id='{self.id}', name='{self.name}')>"

class HomebrewRule(Base):
	"""
	Домашнее правило мастера.
	Реализует требование ТЗ о глубокой поддержке user-generated content.
	"""
	__tablename__ = "homebrew_rules"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)
	owner_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	title: Mapped[str] = mapped_column(String(255), nullable=False)
	json_body: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}") # Содержимое правила

	# Видимость согласно ТЗ: 'global', 'friends_only', 'private'
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="homebrew_rules")
	owner: Mapped["User"] = relationship("User", back_populates="created_homebrew_rules") # (нужно будет добавить связь в User)

	def __repr__(self) -> str:
		return f"<HomebrewRule(id='{self.id}', title='{self.title}', scope='{self.visibility_scope}')>"