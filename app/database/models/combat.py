# app/database/models/combat.py
#
# Боевая система D&D 5e: монстры, их действия/черты, сражения и участники.
# Все строковые ссылки на другие таблицы (Character, Ruleset) разрешаются
# SQLAlchemy во время загрузки — циклических импортов с character.py нет.

from Config.imports import (
	DateTime, func, CheckConstraint,
	Integer, String, Text, Boolean, ForeignKey, SmallInteger, Float,
	relationship, JSON, datetime, Mapped, mapped_column,
)
from app.database.database import Base


# ---------------------------------------------------------------------------
# Monster — бестиарий
# ---------------------------------------------------------------------------

class Monster(Base):
	"""
	Бестиарий. Блоки статов монстров по формату SRD 5e.
	Поддерживает как официальных монстров, так и хоумбрю (is_homebrew=True).
	"""
	__tablename__ = "monsters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
	size: Mapped[str] = mapped_column(
		String(20), nullable=False,
		comment="Tiny, Small, Medium, Large, Huge, Gargantuan"
	)
	type_: Mapped[str] = mapped_column(
		"type", String(50), nullable=False,
		comment="Тип: aberration, beast, celestial, construct, dragon, elemental, "
		        "fey, fiend, giant, humanoid, monstrosity, ooze, plant, undead"
	)
	alignment: Mapped[str | None] = mapped_column(String(30), nullable=True)
	challenge_rating: Mapped[float] = mapped_column(
		Float, nullable=False, default=0.0,
		comment="Показатель опасности (CR): 0, 1/8, 1/4, 1/2, 1, 2, …, 30"
	)
	xp_reward: Mapped[int] = mapped_column(
		Integer, default=0,
		comment="Опыт за победу. Рассчитывается по CR, но может быть переопределён."
	)

	# Броня и хиты
	armor_class: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
	ac_source: Mapped[str | None] = mapped_column(
		String(100), nullable=True,
		comment="Источник КД: 'natural armor', 'plate', 'mage armor'"
	)
	hp_max: Mapped[int] = mapped_column(Integer, nullable=False)
	hp_formula: Mapped[str | None] = mapped_column(
		String(50), nullable=True,
		comment="Формула HP: '8d10+24'"
	)
	temp_hp: Mapped[int] = mapped_column(Integer, default=0)

	# Характеристики
	strength: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
	dexterity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
	constitution: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
	intelligence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
	wisdom: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
	charisma: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)

	# Скорости
	speed_walk: Mapped[int] = mapped_column(SmallInteger, default=30)
	speed_fly: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	speed_swim: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	speed_burrow: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	speed_climb: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

	# Сенсоры и языки
	senses: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="{'darkvision': 60, 'blindsight': 30, 'truesight': 120, 'passive_perception': 14}"
	)
	languages_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Языки: ['Common', 'Draconic'] или {'understands': ['Common'], 'speaks': []}"
	)
	skills_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Бонусы навыков: {'Stealth': 6, 'Perception': 4}"
	)

	# Спасброски и имунитеты
	saving_throws_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Бонусы спасбросков: {'DEX': 5, 'WIS': 4}"
	)
	damage_vulnerabilities_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	damage_resistances_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	damage_immunities_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	condition_immunities_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	# Легендарные/лаирные действия (счётчики и описания)
	legendary_actions_max: Mapped[int] = mapped_column(SmallInteger, default=0)
	legendary_actions_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	lair_actions_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

	# Мета
	lore_text: Mapped[str | None] = mapped_column(Text, nullable=True)
	image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False)
	is_legendary: Mapped[bool] = mapped_column(Boolean(), default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- Связи ---
	actions: Mapped[list["MonsterAction"]] = relationship(
		"MonsterAction",
		back_populates="monster",
		cascade="all, delete-orphan",
		passive_deletes=True,
	)
	traits: Mapped[list["MonsterTrait"]] = relationship(
		"MonsterTrait",
		back_populates="monster",
		cascade="all, delete-orphan",
		passive_deletes=True,
	)
	damage_types: Mapped[list["DamageType"]] = relationship(
		secondary="monster_damage_types",
		backref="monsters",
		lazy="selectin",
	)

	__table_args__ = (
		CheckConstraint("strength >= 1 AND strength <= 30", name="ck_monster_str_range"),
		CheckConstraint("dexterity >= 1 AND dexterity <= 30", name="ck_monster_dex_range"),
		CheckConstraint("constitution >= 1 AND constitution <= 30", name="ck_monster_con_range"),
		CheckConstraint("intelligence >= 1 AND intelligence <= 30", name="ck_monster_int_range"),
		CheckConstraint("wisdom >= 1 AND wisdom <= 30", name="ck_monster_wis_range"),
		CheckConstraint("charisma >= 1 AND charisma <= 30", name="ck_monster_cha_range"),
		CheckConstraint("challenge_rating >= 0", name="ck_monster_cr_non_negative"),
		CheckConstraint("hp_max >= 1", name="ck_monster_hp_positive"),
	)

	def __repr__(self) -> str:
		return f"<Monster(id={self.id}, name='{self.name}', CR={self.challenge_rating})>"

# ---------------------------------------------------------------------------
# MonsterAction — действия монстра (атаки, мультиатака, заклинания…)
# ---------------------------------------------------------------------------

class MonsterAction(Base):
	"""
	Действия монстра: стандартные атаки (Bite, Claws, Breath Weapon),
	мультиатака, применение заклинаний, легендарные действия.
	"""
	__tablename__ = "monster_actions"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	monster_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("monsters.id", ondelete="CASCADE"), nullable=False, index=True,
	)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	action_type: Mapped[str] = mapped_column(
		String(30), nullable=False, default='action',
		comment="Тип: 'action', 'multiattack', 'bonus_action', 'reaction', "
		        "'legendary', 'lair', 'mythic'"
	)
	description: Mapped[str] = mapped_column(Text, nullable=False)

	# Механики атаки
	attack_bonus: Mapped[int | None] = mapped_column(
		SmallInteger, nullable=True,
		comment="Бонус к попаданию (для атак с боевым бонусом)"
	)
	reach_ft: Mapped[int | None] = mapped_column(
		SmallInteger, nullable=True,
		comment="Досягаемость в футах"
	)
	range_normal_ft: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	range_max_ft: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

	damage_dice: Mapped[str | None] = mapped_column(
		String(50), nullable=True,
		comment="Кубы урона: '2d6+4', '4d8'"
	)
	damage_type_slug: Mapped[str | None] = mapped_column(
		String(50), nullable=True,
		comment="Тип урона (строка-ссылка на DamageType.slug): 'piercing', 'fire'"
	)
	secondary_damage_dice: Mapped[str | None] = mapped_column(String(50), nullable=True)
	secondary_damage_type_slug: Mapped[str | None] = mapped_column(String(50), nullable=True)

	# ДЦ спасброска для этого действия
	save_dc: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	save_ability_abbr: Mapped[str | None] = mapped_column(
		String(3), nullable=True,
		comment="Характеристика для спасброска: 'DEX', 'CON', 'WIS'"
	)
	save_success_effect: Mapped[str | None] = mapped_column(
		Text, nullable=True,
		comment="Эффект при успешном спасброске: 'half damage', 'no effect'"
	)

	# Легендарные действия требуют затрат
	legendary_cost: Mapped[int] = mapped_column(SmallInteger, default=1)

	is_recharge: Mapped[bool] = mapped_column(
		Boolean(), default=False,
		comment="Перезаряжаемое действие (Recharge 5-6)"
	)
	recharge_on: Mapped[str | None] = mapped_column(
		String(5), nullable=True,
		comment="Значение d6 для перезарядки: '5-6', '6'"
	)
	uses_per_day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

	# --- Связи ---
	monster: Mapped["Monster"] = relationship("Monster", back_populates="actions")

	def __repr__(self) -> str:
		return f"<MonsterAction(id={self.id}, name='{self.name}', type='{self.action_type}')>"

# ---------------------------------------------------------------------------
# MonsterTrait — особые черты монстра (Amphibious, Pack Tactics…)
# ---------------------------------------------------------------------------

class MonsterTrait(Base):
	"""
	Пассивные и активные черты монстра:
	Amphibious, Pack Tactics, Spellcasting, Regeneration, Magic Resistance и т.д.
	"""
	__tablename__ = "monster_traits"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	monster_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("monsters.id", ondelete="CASCADE"), nullable=False, index=True,
	)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	trait_category: Mapped[str | None] = mapped_column(
		String(30), nullable=True,
		comment="Категория: 'sense', 'defense', 'offense', 'movement', "
		        "'spellcasting', 'other'"
	)

	# --- Связи ---
	monster: Mapped["Monster"] = relationship("Monster", back_populates="traits")

	def __repr__(self) -> str:
		return f"<MonsterTrait(id={self.id}, name='{self.name}')>"

# ---------------------------------------------------------------------------
# Encounter — сражение
# ---------------------------------------------------------------------------

class Encounter(Base):
	"""
	Сражение (Encounter). Группирует монстров и персонажей в одном бою.
	Содержит настройки сложности, правил и контекст (локация, правила).
	"""
	__tablename__ = "encounters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True,
	)
	location_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True,
	)
	ruleset_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True,
		comment="Набор правил, активный в этом бою (домашние правила)"
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	status: Mapped[str] = mapped_column(
		String(20), default='planning',
		comment="Статус: 'planning', 'active', 'paused', 'completed', 'fled'"
	)
	difficulty: Mapped[str] = mapped_column(
		String(20), default='medium',
		comment="Расчётная сложность: 'easy', 'medium', 'hard', 'deadly', 'custom'"
	)
	environment_effects_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Эффекты окружения: лавовые ямы, туман, благословение/проклятие арены"
	)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	# --- Связи ---
	campaign: Mapped["Campaign | None"] = relationship("Campaign")
	location: Mapped["Location | None"] = relationship("Location")
	ruleset: Mapped["Ruleset | None"] = relationship("Ruleset")
	participants: Mapped[list["EncounterParticipant"]] = relationship(
		"EncounterParticipant",
		back_populates="encounter",
		cascade="all, delete-orphan",
		passive_deletes=True,
		order_by="EncounterParticipant.initiative DESC, EncounterParticipant.initiative_tiebreaker",
	)

	def __repr__(self) -> str:
		return f"<Encounter(id={self.id}, name='{self.name}', status='{self.status}')>"

# ---------------------------------------------------------------------------
# EncounterParticipant — участник сражения
# ---------------------------------------------------------------------------

class EncounterParticipant(Base):
	"""
	Участник конкретного сражения.
	Ссылается либо на Character, либо на Monster (одно из полей заполнено).
	"""
	__tablename__ = "encounter_participants"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	encounter_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True,
	)
	character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True,
	)
	monster_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("monsters.id", ondelete="SET NULL"), nullable=True, index=True,
	)

	# Псевдоним для монстра в этом бою (Goblin #3, Boss Orc…)
	display_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

	# Инициатива
	initiative: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
	initiative_tiebreaker: Mapped[float] = mapped_column(
		Float, default=0.0,
		comment="Дробный тибрейкер для одинаковой инициативы (обычно DEX score / 100)"
	)

	# Текущее состояние в бою
	current_hp: Mapped[int] = mapped_column(Integer, nullable=False)
	temp_hp: Mapped[int] = mapped_column(Integer, default=0)
	status_effects_json: Mapped[dict | None] = mapped_column(
		JSON, nullable=True,
		comment="Активные эффекты: {'concentration': True, 'conditions': ['poisoned', 'blinded'], "
		        "'blessed': True, 'shield_of_faith': True}"
	)
	is_surprised: Mapped[bool] = mapped_column(Boolean(), default=False)
	is_concentrating: Mapped[bool] = mapped_column(Boolean(), default=False)
	is_dead: Mapped[bool] = mapped_column(Boolean(), default=False)
	round_entered: Mapped[int] = mapped_column(SmallInteger, default=1)

	notes_dm: Mapped[str | None] = mapped_column(Text, nullable=True)

	# --- Связи ---
	encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="participants")
	character: Mapped["Character | None"] = relationship("Character")
	monster: Mapped["Monster | None"] = relationship("Monster")

	__table_args__ = (
		CheckConstraint(
			"(character_id IS NOT NULL AND monster_id IS NULL) OR "
			"(character_id IS NULL AND monster_id IS NOT NULL)",
			name="ck_encounter_participant_exactly_one_type",
		),
	)

	def __repr__(self) -> str:
		who = f"char={self.character_id}" if self.character_id else f"monster={self.monster_id}"
		return (
			f"<EncounterParticipant(id={self.id}, enc={self.encounter_id}, "
			f"{who}, init={self.initiative}, hp={self.current_hp})>"
		)