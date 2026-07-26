# app/database/models/combat_models.py

from Config.imports import (
	Integer, String, Boolean, ForeignKey, JSONB, Text, func, Table,
	relationship, datetime, DateTime, Mapped, mapped_column, Column)
from app.database.database import Base


encounter_monsters = Table(
	'encounter_monsters',
	Base.metadata,
	Column('encounter_id', Integer, ForeignKey('encounters.id', ondelete="CASCADE"), primary_key=True),
	Column('monster_id', Integer, ForeignKey('monsters.id', ondelete="CASCADE"), primary_key=True),
	# Можно добавить количество здесь, но лучше делать это через Token.amount при создании сцены
)

class Encounter(Base):
	"""
	Столкновение (Набор противников).
	Шаблон группы монстров, готовый к выгрузке на карту.
	"""
	__tablename__ = "encounters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	dungeon_master_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	difficulty_rating: Mapped[float | None] = mapped_column(nullable=True) # Оценка сложности XPBudget по DMG

	is_active: Mapped[bool] = mapped_column(Boolean(), default=False, index=True) # Активен ли сейчас бой?

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	dungeon_master: Mapped["User | None"] = relationship(
		back_populates="active_encounters",
		foreign_keys=[dungeon_master_id]
	)

	# Прямая связь со списком монстров-шаблонов
	monsters: Mapped[list["Monster"]] = relationship(
		secondary="encounter_monsters",
		back_populates="combat_encounters"
	)

	combat_tracker: Mapped["CombatTracker | None"] = relationship(
		uselist=False,
		back_populates="encounter",
		passive_deletes=True
	)

	def __repr__(self) -> str:
		return f"<Encounter(id={self.id}, name='{self.name}', CR_approx={self.difficulty_rating})>"

class Condition(Base):
	"""
	Справочник состояний (Conditions). Пример: Poisoned, Blinded, Paralyzed.
	Является шаблоном для инстанциации Активного эффекта.
	"""
	__tablename__ = "conditions"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Механика SRD
	icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
	is_debuff: Mapped[bool] = mapped_column(Boolean(), default=True)
	prevents_actions: Mapped[bool] = mapped_column(Boolean(), default=False)
	prevents_movement: Mapped[bool] = mapped_column(Boolean(), default=False)
	ends_on_turn_end: Mapped[bool] = mapped_column(Boolean(), default=False)

	# Режим справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	active_effects: Mapped[list["ActiveEffect"]] = relationship(
		back_populates="condition",
		cascade="all, delete-orphan"
	)

	characters: Mapped[list["Character"]] = relationship(
		secondary="character_conditions",
		back_populates="conditions",
		lazy="selectin"
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Condition(id={self.id}, name='{self.name}', status={status})>"

class ActiveEffect(Base):
	"""
	Активный эффект на персонаже или токене.
	Это инстанс применения условия или заклинания.
	"""
	__tablename__ = "active_effects"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	# КТО страдает от эффекта
	character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=True, index=True
	)
	token_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True, index=True
	)

	# ЧТО это за эффект
	condition_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("conditions.id", ondelete="SET NULL"), nullable=True, index=True
	)
	spell_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("spells.id", ondelete="SET NULL"), nullable=True, index=True
	)

	# КТО наложил
	caster_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	# Параметры длительности
	remaining_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Раунды или секунды
	max_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
	concentration_required: Mapped[bool] = mapped_column(Boolean(), default=False)
	effect_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # {atk: 2, save_mod: -1}

	applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	# --- СВЯЗИ ---
	condition: Mapped["Condition | None"] = relationship(back_populates="active_effects")
	spell: Mapped["Spell | None"] = relationship()

	# Привязка к бою (чтобы эффекты снимались при окончании боя)
	combat_tracker_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("combat_trackers.id", ondelete="CASCADE"), nullable=True, index=True
	)
	combat_tracker: Mapped["CombatTracker | None"] = relationship(
		back_populates="active_effects",
		foreign_keys=[combat_tracker_id]
	)

	# Связи с владельцем (для удобства запросов)
	character: Mapped["Character | None"] = relationship(back_populates="active_effects")
	token: Mapped["Token | None"] = relationship(back_populates="active_effects")

	def __repr__(self) -> str:
		target = self.token.character.name if self.token and self.token.character else "Map Object"
		cond_name = self.condition.name if self.condition else "Custom Effect"
		return f"<ActiveEffect(id={self.id}, Target='{target}', Effect='{cond_name}')>"

# ==============================================
#       БОЕВОЙ ТРЕКЕР И ИНИЦИАТИВА
# ==============================================

class CombatTracker(Base):
	"""
	Трекер боя. Управляет очередью хода, раундами и состоянием битвы.
	"""
	__tablename__ = "combat_trackers"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	encounter_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=True, index=True
	)
	location_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
	)

	status: Mapped[str] = mapped_column(String(20), default="ACTIVE") # ACTIVE, PAUSED, FINISHED
	current_round: Mapped[int] = mapped_column(Integer, default=1)
	current_turn_index: Mapped[int] = mapped_column(Integer, default=0)

	turn_duration_seconds: Mapped[int] = mapped_column(Integer, default=60) # Лимит времени на ход
	started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	# --- СВЯЗИ ---
	encounter: Mapped["Encounter | None"] = relationship(back_populates="combat_tracker")

	dungeon_master: Mapped["User | None"] = relationship(
		back_populates="active_encounters",
		foreign_keys=[encounter_id]
	)

	location: Mapped["Location | None"] = relationship()

	initiative_rolls: Mapped[list["InitiativeRoll"]] = relationship(
		back_populates="combat_tracker",
		order_by="desc(InitiativeRoll.initiative_score)",
		cascade="all, delete-orphan"
	)


	# Эффекты, действующие на уровне всего боя (например, Bless)
	active_effects: Mapped[list["ActiveEffect"]] = relationship(
		back_populates="combat_tracker",
		foreign_keys="[ActiveEffect.combat_tracker_id]",
		cascade="all, delete-orphan"
	)

	def __repr__(self) -> str:
		return f"<CombatTracker(id={self.id}, Round={self.current_round}, Status={self.status})>"

class InitiativeRoll(Base):
	"""
	Результат броска инициативы. Определяет место сущности в очереди хода.
	"""
	__tablename__ = "initiative_rolls"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	combat_tracker_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("combat_trackers.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Полиморфная связь: кто именно ходит (Токен может быть как игроком, так и НПС/монстром)
	token_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True, index=True
	)
	character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=True, index=True
	)
	monster_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("monsters.id", ondelete="CASCADE"), nullable=True, index=True
	)

	initiative_score: Mapped[int] = mapped_column(Integer, nullable=False) # Итоговое значение d20 + бонус
	initiative_bonus: Mapped[int] = mapped_column(Integer, default=0)

	has_advantage: Mapped[bool] = mapped_column(Boolean(), default=False)
	has_disadvantage: Mapped[bool] = mapped_column(Boolean(), default=False)

	notes: Mapped[str | None] = mapped_column(String(200), nullable=True) # Например: "Действует Slow"

	# --- СВЯЗИ ---
	combat_tracker: Mapped["CombatTracker"] = relationship(back_populates="initiative_rolls")
	token: Mapped["Token | None"] = relationship()
	character: Mapped["Character | None"] = relationship()
	monster: Mapped["Monster | None"] = relationship()

	def __repr__(self) -> str:
		entity_name = self.token.character.name if self.token and self.token.character else "NPC"
		return f"<Initiative(id={self.id}, Entity='{entity_name}', Score={self.initiative_score})>"