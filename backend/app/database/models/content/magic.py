# backend/app/models/content/magic.py

"""Модели магии: заклинания, школы, уровни."""

from Config.imports import (Mapped, mapped_column, relationship, JSONB, ARRAY, text, uuid4, Table, Column,
                            DateTime, String, Text, Integer, Boolean, ForeignKey, PG_UUID, datetime)
from backend.app.database.database import Base


# --- ЗАКЛИНАНИЯ ---
class Spell(Base):
	"""
	Справочник заклинаний.
	Поддерживает сложные эффекты через json_body и концентрацию.
	"""
	__tablename__ = "spells"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	higher_levels: Mapped[str | None] = mapped_column(Text, nullable=True) # Описание при использовании ячейки выше

	level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0") # 0 - заговор
	school_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("magic_schools.id", ondelete="SET NULL"), nullable=True, index=True
	)

	casting_time: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "1 action"
	range: Mapped[str] = mapped_column(String(100), nullable=False)
	components: Mapped[dict | None] = mapped_column( JSONB, nullable=False, server_default=text("'{\"v\": false, \"s\": false}'::jsonb") )
	duration: Mapped[str] = mapped_column(String(100), nullable=False)

	is_ritual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	requires_concentration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

	classes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True) # ['wizard', 'sorcerer']
	subclasses: Mapped[list[PG_UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)

	damage_types: Mapped[list["DamageType"]] = relationship( "DamageType", secondary="spell_damage_types", back_populates="spells", lazy="selectin" )
	effect_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="spells")
	owner: Mapped["User"] = relationship("User", back_populates="created_spells")
	school: Mapped["MagicSchool"] = relationship("MagicSchool")

	def __repr__(self) -> str:
		return f"<Spell(id='{self.id}', name='{self.name}', level={self.level})>"

# --- УРОВНИ ЗАКЛИНАНИЙ ---
class SpellSlot(Base):
	"""
	Справочник уровней магических ячеек и заговоров.
	Описывает параметры ячейки: уровень слота, количество на уровень в день.
	"""
	__tablename__ = "spell_levels"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew (если мастер меняет прогрессию кастера)
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	level: Mapped[int] = mapped_column(Integer, nullable=False) # 0-9
	name: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "Cantrip", "1st Level"

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Базовая прогрессия по правилам системы (сколько ячеек этого уровня есть у персонажа макс. уровня)
	base_slots_per_day: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

	min_spell_level_to_cast: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
	# Например, чтобы скастовать Fireball (3rd level) из ячейки 4-го уровня,
	# система проверит этот параметр.

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="spell_levels") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_spell_levels")

	def __repr__(self) -> str:
		return f"<SpellSlot(id='{self.id}', level={self.level}, slots={self.base_slots_per_day})>"

# --- ШКОЛЫ МАГИИ ---
class MagicSchool(Base):
	"""
	Справочник школ магии.
	Реализует требование ТЗ о возможности осуждения или запрета школ в лоре мастера.
	"""
	__tablename__ = "magic_schools"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Evocation', 'Necromancy'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Лор и ограничения согласно ТЗ
	is_forbidden_in_setting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	lore_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True) # Текстовое описание запретов мира

	color_theme: Mapped[str | None] = mapped_column(String(7), nullable=True) # HEX цвет для UI (#8B0000 для Некромантии)

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="magic_schools") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_magic_schools")
	spells: Mapped[list["Spell"]] = relationship("Spell", back_populates="school", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<MagicSchool(id='{self.id}', name='{self.name}')>"

# --- СПОСОБНОСТИ ---
class Ability(Base):
	"""
	Справочник способностей.
	Реализует требование ТЗ о «воззваниях колдуна» и иных особых умениях.
	Это могут быть как классовые способности, так и расовые таланты.
	"""
	__tablename__ = "abilities"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Механика активации согласно ТЗ
	activation_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'action', 'bonus_action', 'reaction', 'long_rest'
	uses_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True) # null - неограниченно или зависит от другого ресурса
	recharge_condition: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. 'after_short_rest'

	prerequisites: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"feature": "Pact Boon: Blade", "level": 3}

	effect_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# Машиночитаемый эффект для автоматизации бросков

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="abilities") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_abilities")

	def __repr__(self) -> str:
		return f"<Ability(id='{self.id}', name='{self.name}')>"

# --- ЭФФЕКТЫ ---
class Effect(Base):
	"""
	Модульный справочник эффектов.
	Реализует требование ТЗ о хранении наборов начальных бонусов и состояний.
	Используется как строительный блок для заклинаний, способностей, снаряжения и болезней.
	"""
	__tablename__ = "effects"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'Blinded', 'Fire Damage'
	slug: Mapped[str] = mapped_column(String(100), nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Тип эффекта согласно механике НРИ
	effect_type: Mapped[str] = mapped_column(String(50), nullable=False)
	# enum: ['condition', 'damage_modifier', 'stat_bonus', 'resistance', 'immunity']

	targets: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"stats": ["str", "dex"], "skills": ["stealth"], "saves": ["dex"]}

	value: Mapped[int | None] = mapped_column(Integer, nullable=True) # +2 к спасброску, -1d6 урона
	dice_formula: Mapped[str | None] = mapped_column(String(20), nullable=True) # e.g. '2d8' для лечения или '1d6' для урона

	damage_type_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="SET NULL"), nullable=True, index=True
	)

	duration_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # 'instant', 'timed', 'permanent'
	duration_value: Mapped[int | None] = mapped_column(Integer, nullable=True) # количество раундов/ходов

	concentration_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="effects") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_effects")
	damage_type: Mapped["DamageType"] = relationship("DamageType")

	def __repr__(self) -> str:
		return f"<Effect(id='{self.id}', name='{self.name}', type='{self.effect_type}')>"

# --- ТИПЫ УРОНА ---
class DamageType(Base):
	"""
	Справочник типов урона.
	Реализует требование ТЗ о привязке эффектов и заклинаний к типам урона.
	"""
	__tablename__ = "damage_types"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew (редкие случаи создания своих типов в хоумрульных сеттингах)
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Fire', 'Poison'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True) # Иконка щита/меча с элементом

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="damage_types") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_damage_types")
	effects: Mapped[list["Effect"]] = relationship("Effect", back_populates="damage_type", cascade="all, delete-orphan")
	spells: Mapped[list["Spell"]] = relationship( "Spell", secondary="spell_damage_types", back_populates="damage_types", lazy="selectin" )

	def __repr__(self) -> str:
		return f"<DamageType(id='{self.id}', name='{self.name}')>"

# Ассоциативная таблица Многие-ко-многим между Заклинаниями и Типами урона
# Одно заклинание может наносить несколько типов урона одновременно (например, Гром + Молния)
class SpellDamageType(Base):
	__tablename__ = "spell_damage_types"

	spell_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("spells.id", ondelete="CASCADE"), primary_key=True
	)
	damage_type_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="CASCADE"), primary_key=True
	)