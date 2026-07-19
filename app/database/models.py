from Config.imports import (
	DateTime, func, SQLEnum, Enum, Float, UniqueConstraint,
	Column, Integer, String, Text, Boolean, ForeignKey, SmallInteger,
	relationship, Table, JSON, datetime, Mapped, mapped_column, backref
)
from app.database.database import Base
from app.enums.db_enums import EntityTypeEnum
from app.enums.log_enums import LogLevelEnum, LogAction
from app.enums.user_enums import Role_enums
from app.enums.person_enums import ItemCategory, ProtectionType, MagicItemRarity


# =============================================================================
# БЛОК 1: ИМПОРТЫ, M2M-ТАБЛИЦЫ, ЛОГИРОВАНИЕ, ПОЛЬЗОВАТЕЛИ
# =============================================================================

# --- СВЯЗИ МНОГИХ-КО-МНОГИМ ДЛЯ ПЕРСОНАЖА ---

character_classes = Table(
	'character_classes',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('class_id', Integer, ForeignKey('classes.id'), primary_key=True),
	Column('level', SmallInteger, nullable=False, default=1),
	Column('subclass_id', Integer, ForeignKey('subclasses.id'), nullable=True)
)

character_spells = Table(
	'character_spells',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('spell_id', Integer, ForeignKey('spells.id'), primary_key=True),
	Column('prepared', Boolean(), default=False)
)

character_items = Table(
	'character_items',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('item_id', Integer, ForeignKey('items.id'), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1),
	Column('equipped', Boolean(), default=False)
)

character_abilities_m2m = Table(
	'character_abilities_m2m',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ability_type_id', Integer, ForeignKey('ability_types.id'), primary_key=True),
	Column('score', SmallInteger, nullable=False, default=8),
	UniqueConstraint('character_id', 'ability_type_id', name='uq_character_ability_m2m')
)

skill_proficiencies_m2m = Table(
	'skill_proficiencies_m2m',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True),
	Column('is_expertise', Boolean(), default=False),
	Column('proficient', Boolean(), default=True),
	UniqueConstraint('character_id', 'skill_id', name='uq_character_skill_m2m')
)

character_feats = Table(
	'character_feats',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('feat_id', Integer, ForeignKey('feats.id'), primary_key=True),
	UniqueConstraint('character_id', 'feat_id', name='uq_character_feat')
)

character_languages = Table(
	'character_languages',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('language_id', Integer, ForeignKey('languages.id'), primary_key=True),
	UniqueConstraint('character_id', 'language_id', name='uq_character_language')
)

character_equipment = Table(
	'character_equipment',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('equipment_id', Integer, ForeignKey('equipment.id'), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1),
	Column('is_attuned', Boolean(), default=False),
	Column('attunement_slots_used', SmallInteger, default=0),
	Column('equipped', Boolean(), default=False),
	UniqueConstraint('character_id', 'equipment_id', name='uq_character_equipment')
)

character_allies = Table(
	'character_allies',
	Base.metadata,
	Column('owner_character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ally_character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('control_type', String(20), nullable=False, default='summon'),
	Column('is_permanent', Boolean(), default=False),
	UniqueConstraint('owner_character_id', 'ally_character_id', name='uq_owner_ally')
)

character_conditions = Table(
	'character_conditions',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('condition_id', Integer, ForeignKey('conditions.id'), primary_key=True),
	Column('source_character_id', Integer, ForeignKey('characters.id', ondelete="SET NULL"), nullable=True),
	Column('source_spell_id', Integer, ForeignKey('spells.id', ondelete="SET NULL"), nullable=True),
	Column('duration_type', String(20), default='instant'),
	Column('duration_value', Integer, nullable=True),
	Column('remaining_duration', Integer, nullable=True),
	Column('concentration_required', Boolean(), default=False),
	Column('is_active', Boolean(), default=True),
	Column('stackable', Boolean(), default=False),
	Column('applied_at', DateTime(timezone=True), server_default=func.now()),
	UniqueConstraint('character_id', 'condition_id', 'source_spell_id', name='uq_char_cond_source')
)

container_items = Table(
	'container_items',
	Base.metadata,
	Column('container_equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('item_equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1)
)

shop_inventory = Table(
	'shop_inventory',
	Base.metadata,
	Column('equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('price_cp', Integer, nullable=False)
)

# Дополнительные M2M-таблицы для связей с DamageType
spell_damage_types = Table(
	'spell_damage_types',
	Base.metadata,
	Column('spell_id', Integer, ForeignKey('spells.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True),
	UniqueConstraint('spell_id', 'damage_type_id', name='uq_spell_damage_type')
)

equipment_damage_types = Table(
	'equipment_damage_types',
	Base.metadata,
	Column('equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True),
	UniqueConstraint('equipment_id', 'damage_type_id', name='uq_equip_damage_type')
)

monster_damage_types = Table(
	'monster_damage_types',
	Base.metadata,
	Column('monster_action_id', Integer, ForeignKey('monster_actions.id', ondelete="CASCADE"), primary_key=True),
	Column('damage_type_id', Integer, ForeignKey('damage_types.id', ondelete="CASCADE"), primary_key=True),
	UniqueConstraint('monster_action_id', 'damage_type_id', name='uq_monster_damage_type')
)

character_saving_throws = Table(
	'character_saving_throws',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ability_type_id', Integer, ForeignKey('ability_types.id', ondelete="CASCADE"), primary_key=True),
	Column('is_proficient', Boolean(), default=False),
	UniqueConstraint('character_id', 'ability_type_id', name='uq_char_saving_throw')
)

# --- ЛОГИРОВАНИЕ И ПОЛЬЗОВАТЕЛИ ---

class UserLog(Base):
	__tablename__ = "user_logs"
	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	action = Column(SQLEnum(LogAction, literal_bindparam=True), nullable=False, index=True)
	description = Column(Text, nullable=True)
	log_level = Column(SQLEnum(LogLevelEnum, literal_bindparam=True), nullable=False, default=LogLevelEnum.INFO, index=True)
	timestamp = Column(DateTime, default=datetime.utcnow, index=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	user = relationship("User", back_populates="logs")

	def __repr__(self):
		return f"<UserLog(id='{self.id}', user_id='{self.user_id}', action='{self.action}', level='{self.log_level}')>"

class AppLog(Base):
	__tablename__ = "app_logs"
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(50), nullable=True, index=True)
	action = Column(SQLEnum(LogAction, literal_bindparam=True), nullable=False, index=True)
	description = Column(Text, nullable=True)
	timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
	log_level = Column(SQLEnum(LogLevelEnum, literal_bindparam=True), nullable=False, default=LogLevelEnum.INFO, index=True)

	def __repr__(self):
		return f"<AppLog(id='{self.id}', username='{self.username}', action='{self.action}', level='{self.log_level}')>"

class User(Base):
	__tablename__ = "users"
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(50), unique=True, nullable=False, index=True)
	hashed_password = Column(String(255), nullable=False)
	is_active = Column(Boolean(), default=True)
	role = Column(Enum(Role_enums), default=Role_enums.PLAYER, nullable=False)
	gdpr_consent = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	characters = relationship("Character", back_populates="user", foreign_keys="Character.user_id", passive_deletes=True)
	logs = relationship("UserLog", back_populates="user", order_by=UserLog.timestamp.desc(), passive_deletes=True)
	rules_created = relationship("Ruleset", back_populates="owner", foreign_keys="Ruleset.owner_id")
	homebrew_entities = relationship("HomebrewEntity", back_populates="creator", foreign_keys="HomebrewEntity.creator_id", passive_deletes=True)

	def __repr__(self):
		return f"<User(username='{self.username}', role='{self.role}')>"


# =============================================================================
# БЛОК 2: ПРАВИЛА, РАСЫ, КЛАССЫ, ЗАКЛИНАНИЯ, ПРЕДМЕТЫ
# =============================================================================

class CalculationField(Base):
	"""
	Справочник всех динамически рассчитываемых полей персонажа или существа.
	Позволяет правилам ссылаться на конкретные данные по ID, а не по строке.
	"""
	__tablename__ = "calculation_fields"
	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
	field_path: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	display_name: Mapped[str] = mapped_column(String(100), nullable=False)
	data_type: Mapped[str] = mapped_column(String(20), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	def __repr__(self):
		return f"<CalcField(path='{self.field_path}', name='{self.display_name}')>"

class RulesetModifier(Base):
	"""
	Модификаторы правил для конкретного набора правил (Ruleset).
	Узел вычислительного графа. Определяет, КАК меняется поле из CalculationField.
	"""
	__tablename__ = "ruleset_modifiers"
	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	ruleset_id: Mapped[int] = mapped_column(Integer, ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False, index=True)
	calculation_field_id: Mapped[int] = mapped_column(Integer, ForeignKey("calculation_fields.id", ondelete="CASCADE"), nullable=False, index=True)
	depends_on_modifier_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ruleset_modifiers.id", ondelete="SET NULL"), nullable=True, index=True)
	priority: Mapped[int] = mapped_column(SmallInteger, default=100, nullable=False)
	modifier_type: Mapped[str] = mapped_column(String(30), nullable=False)
	config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
	condition_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
	ruleset: Mapped["Ruleset"] = relationship(back_populates="modifiers")
	target_field: Mapped["CalculationField"] = relationship()
	depends_on: Mapped["RulesetModifier | None"] = relationship(remote_side=[id], backref="dependent_modifiers")

	__table_args__ = (
		UniqueConstraint('ruleset_id', 'calculation_field_id', 'priority', name='uq_ruleset_field_priority'),
	)

	def __repr__(self):
		return f"<RulesetModifier(rule={self.ruleset_id}, field='{self.calculation_field_id}', type='{self.modifier_type}')>"

class Ruleset(Base):
	"""Набор правил игры (домашние правила или выбор из пресетов)"""
	__tablename__ = "rulesets"
	id = Column(Integer, primary_key=True, index=True)
	owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	parent_ruleset_id = Column(Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True)
	name = Column(String(100), nullable=False)
	is_public = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	characters = relationship("Character", back_populates="ruleset")
	owner = relationship("User", back_populates="rules_created", foreign_keys=[owner_id])
	parent_ruleset = relationship("Ruleset", remote_side=[id], backref="child_rulesets")

	is_custom_ruleset: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)

	modifiers: Mapped[list["RulesetModifier"]] = relationship(
		back_populates="ruleset", cascade="all, delete-orphan", order_by="RulesetModifier.priority"
	)
	homebrew_entities: Mapped[list["HomebrewEntity"]] = relationship(
		back_populates="ruleset", foreign_keys="HomebrewEntity.ruleset_id"
	)

	def __repr__(self):
		mode = "Custom" if self.is_custom_ruleset else "Standard 5e"
		return f"<Ruleset(id='{self.id}', name='{self.name}', mode='{mode}')>"

class Race(Base):
	"""Расы персонажей (Human, Elf, Dwarf и т.д.)"""
	__tablename__ = "races"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	size = Column(String(20), nullable=False)
	speed = Column(SmallInteger, nullable=False, default=30)
	languages_base = Column(JSON, nullable=True)
	ability_bonuses_json = Column(JSON, nullable=True)
	traits_description = Column(Text, nullable=True)

	homebrew_variants = relationship("HomebrewEntity", back_populates="parent_entity",
	                                 foreign_keys="HomebrewEntity.parent_canon_id",
	                                 primaryjoin="and_(Race.id == HomebrewEntity.parent_canon_id, "
	                                             "HomebrewEntity.entity_type == EntityTypeEnum.RACE)")

	def __repr__(self):
		return f"<Race(name='{self.name}')>"

class Background(Base):
	"""Предыстории персонажей (Soldier, Criminal, Sage и т.д.)"""
	__tablename__ = "backgrounds"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	skills_granted = Column(JSON, nullable=True)
	languages_granted = Column(JSON, nullable=True)
	tool_proficiencies = Column(JSON, nullable=True)
	feature_name = Column(String(100), nullable=True)
	feature_description = Column(Text, nullable=True)

	def __repr__(self):
		return f"<Background(name='{self.name}')>"

class Class_(Base):
	"""Классы персонажей (Fighter, Wizard, Rogue и т.д.)"""
	__tablename__ = "classes"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	hit_die = Column(SmallInteger, nullable=False)
	primary_ability = Column(String(50), nullable=True)
	saving_throw_proficiencies = Column(JSON, nullable=True)
	armor_proficiencies = Column(JSON, nullable=True)
	weapon_proficiencies = Column(JSON, nullable=True)
	tools_proficiencies = Column(JSON, nullable=True)
	multiclass_requirements_json = Column(JSON, nullable=True)
	description = Column(Text, nullable=True)
	subclasses = relationship("Subclass", back_populates="parent_class")

	def __repr__(self):
		return f"<Class(name='{self.name}')>"

class Subclass(Base):
	"""Подклассы (Arcane Trickster, Champion, Wild Magic Sorcerer и т.д.)"""
	__tablename__ = "subclasses"
	id = Column(Integer, primary_key=True, index=True)
	parent_class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	description = Column(Text, nullable=True)
	parent_class = relationship("Class_", back_populates="subclasses")

	def __repr__(self):
		return f"<Subclass(name='{self.name}', class='{self.parent_class.name}')>"

class Spell(Base):
	"""Заклинания"""
	__tablename__ = "spells"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	level = Column(SmallInteger, nullable=False, default=0)
	school = Column(String(30), nullable=False)
	casting_time = Column(String(50), nullable=False)
	range_ = Column(String(50), nullable=False)
	components = Column(String(100), nullable=False)
	duration = Column(String(50), nullable=False)
	is_ritual = Column(Boolean(), default=False)
	classes_allowed = Column(JSON, nullable=True)
	description = Column(Text, nullable=False)
	higher_levels = Column(Text, nullable=True)

	damage_types: Mapped[list["DamageType"]] = relationship(secondary=spell_damage_types, backref="spells")

	def __repr__(self):
		return f"<Spell(name='{self.name}', level={self.level})>"

class Item(Base):
	"""Предметы (общее определение, включая оружие, броню, расходники)"""
	__tablename__ = "items"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	category = Column(SQLEnum(ItemCategory, literal_bindparam=True), nullable=False)
	rarity = Column(SQLEnum(MagicItemRarity, literal_bindparam=True), nullable=True)
	weight = Column(Float, nullable=False, default=0.0)
	cost_cp = Column(Integer, nullable=True)
	description = Column(Text, nullable=True)
	properties_json = Column(JSON, nullable=True)

	def __repr__(self):
		return f"<Item(name='{self.name}', category='{self.category.value}')>"

# =============================================================================
# БЛОК 3: ХОУМБРЮ-ДВИЖОК И ВСПОМОГАТЕЛЬНЫЕ СПРАВОЧНИКИ
# =============================================================================

class HomebrewEntity(Base):
	"""
	Базовая сущность для любого кастомного контента.
	Позволяет переопределять официальные книги (PHB, DMG) или добавлять абсолютно новые сущности.
	"""
	__tablename__ = "homebrew_entities"
	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	ruleset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), index=True)
	entity_type: Mapped[EntityTypeEnum] = mapped_column(SQLEnum(EntityTypeEnum, literal_bindparam=True), nullable=False, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
	parent_canon_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
	parent_canon_type: Mapped[EntityTypeEnum | None] = mapped_column(SQLEnum(EntityTypeEnum, literal_bindparam=True), nullable=True)
	freeform_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	rules_patch: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	is_approved: Mapped[bool] = mapped_column(Boolean(), default=False)
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

	creator: Mapped["User"] = relationship(back_populates="homebrew_entities")
	ruleset: Mapped["Ruleset"] = relationship(
		back_populates="homebrew_entities",
		foreign_keys=[ruleset_id]
	)
	parent_entity: Mapped["HomebrewEntity | None"] = relationship(
		remote_side=[id],
		backref="child_variants"
	)

	def __repr__(self):
		status = "Active" if self.is_active else "Disabled"
		return f"<HomebrewEntity(v{self.version}, type='{self.entity_type.value}', name='{self.name}', status='{status}')>"

class AbilityType(Base):
	"""Типы характеристик: 6 базовых (STR/DEX/CON/INT/WIS/CHA) + кастомные (Удача, Мана, Честь)"""
	__tablename__ = "ability_types"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True) # Strength, Dexterity, Luck, Mana
	abbreviation = Column(String(3), nullable=False, unique=True) # STR, DEX, LCK, MAN
	is_custom = Column(Boolean(), default=False)
	description = Column(Text, nullable=True)

	def __repr__(self):
		return f"<AbilityType(name='{self.name}', abbr='{self.abbreviation}')>"

class Skill(Base):
	"""Навыки: 18 базовых + кастомные (инструменты, ремёсла)"""
	__tablename__ = "skills"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True) # Stealth, Arcana, Thieves' Tools
	slug = Column(String(100), nullable=False, unique=True, index=True)
	linked_ability_abbr = Column(String(3), nullable=True) # DEX, INT
	skill_category = Column(String(20), nullable=False, default='skill') # skill, tool, vehicle
	description = Column(Text, nullable=True)
	is_custom = Column(Boolean(), default=False)

	def __repr__(self):
		return f"<Skill(name='{self.name}', abil='{self.linked_ability_abbr}')>"

class Feat(Base):
	"""Черты (Alert, Lucky, Great Weapon Master и т.д.)"""
	__tablename__ = "feats"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	prerequisite_json = Column(JSON, nullable=True)
	bonus_json = Column(JSON, nullable=True)
	description = Column(Text, nullable=False)
	is_homebrew = Column(Boolean(), default=False)

	def __repr__(self):
		return f"<Feat(name='{self.name}')>"

class Language(Base):
	"""Языки (Common, Elvish, Draconic, Thieves' Cant и т.д.)"""
	__tablename__ = "languages"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	script = Column(String(50), nullable=True)
	is_exotic = Column(Boolean(), default=False)
	is_secret = Column(Boolean(), default=False)
	description = Column(Text, nullable=True)

	def __repr__(self):
		return f"<Language(name='{self.name}')>"

class Condition(Base):
	"""Состояния (Blinded, Charmed, Poisoned, Exhaustion и т.д.)"""
	__tablename__ = "conditions"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	effects_json = Column(JSON, nullable=True)
	is_custom = Column(Boolean(), default=False)
	description = Column(Text, nullable=True)

	def __repr__(self):
		return f"<Condition(name='{self.name}')>"

class Organization(Base):
	"""Организации/фракции (Гильдия Воров, Арфисты, Жентарим и т.д.)"""
	__tablename__ = "organizations"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	description = Column(Text, nullable=True)
	alignment = Column(String(20), nullable=True)
	leader_character_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
	is_secret = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

	leader = relationship("Character", foreign_keys=[leader_character_id])
	members = relationship("Character", back_populates="organization", foreign_keys="Character.organization_id")

	def __repr__(self):
		return f"<Organization(name='{self.name}')>"

class ShopVendor(Base):
	"""Магазины/торговцы (стационарные лавки, странствующие караваны)"""
	__tablename__ = "shops"
	id = Column(Integer, primary_key=True, index=True)
	owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
	name = Column(String(100), nullable=False)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	shop_type = Column(String(50), nullable=False) # general, magic, weapons, armor, potions
	description = Column(Text, nullable=True)
	buy_markup_multiplier = Column(Float, default=1.0)
	sell_discount_multiplier = Column(Float, default=0.5)
	is_traveling = Column(Boolean(), default=False)
	restock_frequency = Column(String(20), default='session')
	gold_reserve = Column(Integer, default=0)

	owner = relationship("User")
	location = relationship("Location")

	def __repr__(self):
		return f"<ShopVendor(name='{self.name}', type='{self.shop_type}')>"

# =============================================================================
# БЛОК 4: ПЕРСОНАЖ, ХАРАКТЕРИСТИКИ, НАВЫКИ, УРОВНИ, СПАСБРОСКИ
# =============================================================================

class Character(Base):
	"""Персонажи игроков и NPC"""
	__tablename__ = "characters"
	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	ruleset_id = Column(Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True)
	organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
	race_id = Column(Integer, ForeignKey("races.id", ondelete="RESTRICT"), nullable=False, index=True)
	background_id = Column(Integer, ForeignKey("backgrounds.id", ondelete="RESTRICT"), nullable=True, index=True)

	name = Column(String(100), nullable=False)
	slug = Column(String(100), nullable=False, unique=True, index=True)
	character_type = Column(String(20), nullable=False, default="PC")
	alignment = Column(String(20), default="Neutral")
	deity = Column(String(100), nullable=True)
	portrait_url = Column(String(255), nullable=True)
	bio = Column(Text, nullable=True)
	stats_json = Column(JSON, nullable=True)

	experience = Column(Integer, nullable=False, default=0)
	total_experience_points = Column(Integer, default=0)
	proficiency_bonus = Column(SmallInteger, default=2)

	level_history = relationship("CharacterLevel", back_populates="character", cascade="all, delete-orphan", order_by="CharacterLevel.level_number")
	spell_slots: Mapped[list["SpellSlot"]] = relationship(
		back_populates="character",
		cascade="all, delete-orphan",
		lazy="select"
	)

	@property
	def current_level(self):
		if not self.level_history:
			return 0
		return max(level.level_number for level in self.level_history)

	user = relationship("User", back_populates="characters")
	ruleset = relationship("Ruleset", back_populates="characters")
	organization = relationship("Organization", back_populates="members")
	race = relationship("Race")
	background = relationship("Background")

	abilities_detail: Mapped[list["CharacterAbilityValue"]] = relationship(
		back_populates="character", cascade="all, delete-orphan", lazy="joined"
	)
	skills_detail: Mapped[list["SkillProficiency"]] = relationship(
		back_populates="character", cascade="all, delete-orphan", lazy="joined"
	)
	saving_throws: Mapped[list["SavingThrow"]] = relationship(
		back_populates="character", cascade="all, delete-orphan", lazy="joined"
	)
	feats: Mapped[list["Feat"]] = relationship(secondary=character_feats, backref="holders")
	languages: Mapped[list["Language"]] = relationship(secondary=character_languages, backref="speakers")
	equipment: Mapped[list["Equipment"]] = relationship(back_populates="character", cascade="all, delete-orphan")
	controlled_allies: Mapped[list["Character"]] = relationship(
		secondary=character_allies,
		primaryjoin=(character_allies.c.owner_character_id == id),
		secondaryjoin=(character_allies.c.ally_character_id == id),
		backref="controller",
		lazy="select"
	)
	conditions: Mapped[list["Condition"]] = relationship(secondary=character_conditions, backref="active_conditions")

	def __repr__(self):
		return f"<Character(name='{self.name}', lvl={self.current_level}, xp={self.experience})>"

class CharacterAbilityValue(Base):
	"""
	Конкретное значение характеристики у персонажа.
	Использует таблицу-справочник ability_types для поддержки кастомных статов (Мана, Удача).
	"""
	__tablename__ = "character_abilities"
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
	ability_type_id = Column(Integer, ForeignKey("ability_types.id", ondelete="CASCADE"), primary_key=True)
	score = Column(SmallInteger, nullable=False, default=8)
	character = relationship("Character", back_populates="abilities_detail")
	type = relationship("AbilityType")
	__table_args__ = (
		UniqueConstraint('character_id', 'ability_type_id', name='uq_char_ability_val'),
	)

	def __repr__(self):
		return f"<CharAbility(char={self.character_id}, abil='{self.type.name}', val={self.score})>"

class SkillProficiency(Base):
	"""
	Владение навыком или инструментом персонажем с возможностью хранить доп. флаги (экспертиза).
	Объединяет классические навыки (Skills) и инструменты (Tools/Vehicles).
	"""
	__tablename__ = "skill_proficiencies"
	character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
	skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)

	proficiency_category: Mapped[str] = mapped_column(
		String(20),
		nullable=False,
		default='skill',
		index=True,
		server_default='skill'
	)

	is_expertise: Mapped[bool] = mapped_column(Boolean(), default=False)
	proficient: Mapped[bool] = mapped_column(Boolean(), default=True)
	character: Mapped["Character"] = relationship(back_populates="skills_detail")
	skill: Mapped["Skill"] = relationship()
	__table_args__ = (
		UniqueConstraint('character_id', 'skill_id', name='uq_char_skill_prof'),
	)

	def __repr__(self):
		status = "Expert" if self.is_expertise else ("Yes" if self.proficient else "No")
		return f"<SkillProf(char={self.character_id}, skill='{self.skill.name}', cat='{self.proficiency_category}', prof={status})>"

class CharacterLevel(Base):
	"""
	История уровней персонажа. Решает проблему пересчета HP при изменении прошлых уровней.
	Хранит данные о том, на каком этапе был взят конкретный класс/подкласс.
	"""
	__tablename__ = "character_levels"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey('characters.id', ondelete="CASCADE"), nullable=False, index=True)
	class_id = Column(Integer, ForeignKey('classes.id'), nullable=False, index=True)
	subclass_id = Column(Integer, ForeignKey('subclasses.id'), nullable=True, index=True)
	level_number = Column(SmallInteger, nullable=False)
	experience_at_level = Column(Integer, nullable=False)
	hit_dice_collected_json = Column(JSON, nullable=False)
	features_unlocked_json = Column(JSON, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

	character = relationship("Character", back_populates="level_history")
	dnd_class = relationship("Class_")
	subclass = relationship("Subclass")

	__table_args__ = (
		UniqueConstraint('character_id', 'level_number', name='uq_character_level_num'),
	)

	def __repr__(self):
		sub_name = f", {self.subclass.name}" if self.subclass else ""
		return f"<CharLvl(char={self.character_id}, cls={self.dnd_class.name}{sub_name}, lvl={self.level_number})>"

class SavingThrow(Base):
	"""
	Спасброски персонажа: владение + бонусы от предметов/эффектов.
	"""
	__tablename__ = "saving_throws"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
	ability_type_id = Column(Integer, ForeignKey("ability_types.id", ondelete="CASCADE"), nullable=False)
	is_proficient = Column(Boolean(), default=False)
	bonus_override = Column(SmallInteger, nullable=True)
	notes = Column(Text, nullable=True)

	character = relationship("Character", back_populates="saving_throws")
	ability_type = relationship("AbilityType")

	__table_args__ = (
		UniqueConstraint('character_id', 'ability_type_id', name='uq_char_save'),
	)

	def __repr__(self):
		prof = "Prof" if self.is_proficient else "NoProf"
		return f"<SavingThrow(char={self.character_id}, abil='{self.ability_type.abbreviation}', {prof})>"

class SpellSlot(Base):
	"""
	Доступные ячейки заклинаний конкретного персонажа.
	Хранит текущее состояние ресурсов мага после короткого/длинного отдыха.
	"""
	__tablename__ = "spell_slots"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey('characters.id', ondelete="CASCADE"), nullable=False, index=True)
	spell_level = Column(SmallInteger, nullable=False)
	slots_total = Column(SmallInteger, nullable=False)
	slots_used = Column(SmallInteger, default=0)
	character = relationship("Character", back_populates="spell_slots")
	__table_args__ = (
		UniqueConstraint('character_id', 'spell_level', name='uq_char_spell_slot'),
	)

	def __repr__(self):
		return f"<SpellSlot(char={self.character_id}, lvl={self.spell_level}, used={self.slots_used}/{self.slots_total})>"

# =============================================================================
# БЛОК 5: ИНВЕНТАРЬ, ЭКИПИРОВКА, ЭКОНОМИКА
# =============================================================================

class EquipmentSlot(Base):
	"""Слоты для экипировки (слот оружия, слот брони, кольца и т.д.)"""
	__tablename__ = "equipment_slots"
	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	slot_type: Mapped[str] = mapped_column(String(20), nullable=False)
	max_items: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
	equipment: Mapped[list["Equipment"]] = relationship("Equipment", backref="slot")

	def __repr__(self):
		return f"<EquipmentSlot(name='{self.name}', type='{self.slot_type}')>"

class DamageType(Base):
	"""Типы урона (Огонь, Рубящий, Яд и т.д.)"""
	__tablename__ = "damage_types"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True)
	slug = Column(String(50), nullable=False, unique=True, index=True)
	description = Column(Text, nullable=True)

	def __repr__(self):
		return f"<DamageType(name='{self.name}')>"

class Equipment(Base):
	"""Снаряжение (конкретные экземпляры предметов в сумке или на теле)"""
	__tablename__ = "equipment"
	id = Column(Integer, primary_key=True, index=True)
	item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
	character_id = Column(Integer, ForeignKey('characters.id', ondelete="SET NULL"), nullable=True, index=True)

	slot_id = Column(Integer, ForeignKey('equipment_slots.id'), nullable=True, index=True)
	name_override = Column(String(100), nullable=True)
	notes = Column(Text, nullable=True)
	current_durability = Column(SmallInteger, nullable=True)
	charges = Column(SmallInteger, nullable=True)
	protection_type = Column(SQLEnum(ProtectionType, literal_bindparam=True), nullable=True)
	ac_bonus = Column(SmallInteger, nullable=True)
	damage_dice = Column(String(20), nullable=True)
	damage_type = Column(String(20), nullable=True)
	magical_effects = Column(JSON, nullable=True)
	is_identified = Column(Boolean(), default=False)
	requires_attunement = Column(Boolean(), default=False)
	attunement_by_class = Column(JSON, nullable=True)
	attunement_by_race = Column(JSON, nullable=True)
	resale_value_modifier = Column(Float, default=1.0)

	item = relationship("Item")
	slot = relationship("EquipmentSlot", back_populates="equipment")
	contained_items = relationship("Equipment", secondary="container_items",
	                               primaryjoin=(id == "container_items.c.container_equipment_id"),
	                               secondaryjoin=(id == "container_items.c.item_equipment_id"),
	                               lazy="select", backref="parent_container")
	damage_types: Mapped[list["DamageType"]] = relationship(secondary=equipment_damage_types, backref="equipment_items")
	character: Mapped["Character"] = relationship("Character", back_populates="equipment", foreign_keys=[character_id])

	def __repr__(self):
		display_name = self.name_override or self.item.name
		owner = f"char_id={self.character_id}" if self.character_id else "storage"
		return f"<Equip(id={self.id}, name='{display_name}', owner={owner})>"

class CurrencyType(Base):
	"""Типы валюты (CP, SP, GP, Platinum, экзотические монеты)"""
	__tablename__ = "currency_types"
	id = Column(Integer, primary_key=True, index=True)
	symbol = Column(String(10), nullable=False, unique=True)
	name = Column(String(50), nullable=False)
	conversion_to_gp = Column(Float, nullable=False, default=1.0)
	is_standard = Column(Boolean(), default=True)

	def __repr__(self):
		return f"<CurrencyType(symbol='{self.symbol}', gp_value={self.conversion_to_gp})>"

class CharacterWallet(Base):
	"""Кошелёк персонажа: баланс по каждой валюте отдельно"""
	__tablename__ = "character_wallets"
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
	currency_id = Column(Integer, ForeignKey("currency_types.id", ondelete="CASCADE"), primary_key=True)
	amount = Column(Integer, nullable=False, default=0)
	character = relationship("Character")
	currency = relationship("CurrencyType")

	def __repr__(self):
		return f"<CharacterWallet(char={self.character_id}, cur='{self.currency.symbol}', amt={self.amount})>"

class TransactionLog(Base):
	"""Журнал транзакций (покупки, награды, штрафы, изъятие мастером)"""
	__tablename__ = "transaction_logs"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)
	shop_id = Column(Integer, ForeignKey("shops.id", ondelete="SET NULL"), nullable=True, index=True)
	dm_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	transaction_type = Column(String(30), nullable=False)
	currency_id = Column(Integer, ForeignKey("currency_types.id", ondelete="RESTRICT"), nullable=False)
	amount = Column(Integer, nullable=False)
	item_id = Column(Integer, ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
	notes = Column(Text, nullable=True)
	timestamp = Column(DateTime(timezone=True), server_default=func.now())

	character = relationship("Character")
	shop = relationship("ShopVendor")
	dm = relationship("User")
	currency = relationship("CurrencyType")
	item = relationship("Item")

	def __repr__(self):
		return (f"<TransactionLog(type='{self.transaction_type}', amount={self.amount}, "
		        f"cur='{self.currency.symbol}')>")


# =============================================================================
# БЛОК 6: БОЕВАЯ СИСТЕМА, МОНСТРЫ, КАМПАНИИ, КВЕСТЫ, ЛОКАЦИИ, ЗАМЕТКИ
# =============================================================================

class Encounter(Base):
	"""Сражение/встреча (сессия боя)"""
	__tablename__ = "encounters"
	id = Column(Integer, primary_key=True, index=True)
	ruleset_id = Column(Integer, ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	description = Column(Text, nullable=True)
	dm_notes = Column(Text, nullable=True)
	initiative_order_json = Column(JSON, nullable=True)
	is_active = Column(Boolean(), default=True)
	started_at = Column(DateTime(timezone=True), nullable=True)
	ended_at = Column(DateTime(timezone=True), nullable=True)

	ruleset = relationship("Ruleset")
	participants = relationship("EncounterParticipant", back_populates="encounter", cascade="all, delete-orphan")

	def __repr__(self):
		return f"<Encounter(name='{self.name}', active={self.is_active})>"

class EncounterParticipant(Base):
	"""Участники встречи (персонажи и монстры в бою)"""
	__tablename__ = "encounter_participants"
	id = Column(Integer, primary_key=True, index=True)
	encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)
	monster_id = Column(Integer, ForeignKey("monsters.id", ondelete="SET NULL"), nullable=True, index=True)
	initiative_roll = Column(SmallInteger, nullable=True)
	turn_order = Column(SmallInteger, nullable=True)
	current_hp = Column(Integer, nullable=True)
	temp_hp = Column(Integer, default=0)
	status_flags_json = Column(JSON, nullable=True)

	encounter = relationship("Encounter", back_populates="participants")
	character = relationship("Character")
	monster = relationship("Monster")

	def __repr__(self):
		name = (self.character.name if self.character else
		        (self.monster.name if self.monster else "Unknown"))
		return f"<EncounterParticipant(enc={self.encounter_id}, name='{name}', init={self.initiative_roll})>"

class Monster(Base):
	"""Блок статистики существа (Monster Stat Block) по стандартам D&D 5e"""
	__tablename__ = "monsters"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	size = Column(String(20), nullable=False)
	type_creature = Column(String(50), nullable=False)
	subtype = Column(String(50), nullable=True)
	alignment = Column(String(20), default="Unaligned")
	armor_class = Column(SmallInteger, nullable=False)
	armor_type = Column(String(50), nullable=True)
	hit_points = Column(Integer, nullable=False)
	hit_dice_formula = Column(String(20), nullable=False)
	speed_walk = Column(SmallInteger, nullable=False, default=30)
	speeds_json = Column(JSON, nullable=True)
	saving_throws_json = Column(JSON, nullable=True)
	skills_json = Column(JSON, nullable=True)
	damage_vulnerabilities = Column(String(100), nullable=True)
	damage_resistances = Column(JSON, nullable=True)
	damage_immunities = Column(JSON, nullable=True)
	condition_immunities = Column(JSON, nullable=True)
	senses_json = Column(JSON, nullable=True)
	languages = Column(JSON, nullable=True)
	challenge_rating = Column(Float, nullable=False)
	experience_reward = Column(Integer, nullable=False)
	description_text = Column(Text, nullable=True)

	actions = relationship("MonsterAction", back_populates="monster", cascade="all, delete-orphan")
	traits = relationship("MonsterTrait", back_populates="monster", cascade="all, delete-orphan")

	def __repr__(self):
		return f"<Monster(name='{self.name}', cr={self.challenge_rating})>"

class MonsterAction(Base):
	"""Действия в блоке статистики (Actions/Reactions/Legendary Actions)"""
	__tablename__ = "monster_actions"
	id = Column(Integer, primary_key=True, index=True)
	monster_id = Column(Integer, ForeignKey('monsters.id', ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	action_type = Column(String(20), nullable=False)
	usage_limit = Column(String(20), nullable=True)
	attack_bonus = Column(SmallInteger, nullable=True)
	reach_distance = Column(SmallInteger, nullable=True)
	range_data = Column(JSON, nullable=True)
	damage_json = Column(JSON, nullable=True)
	damage_2ndary_json = Column(JSON, nullable=True)
	save_effect_json = Column(JSON, nullable=True)
	description = Column(Text, nullable=True)
	monster = relationship("Monster", back_populates="actions")

	damage_types: Mapped[list["DamageType"]] = relationship(secondary=monster_damage_types, backref="monster_actions")

	def __repr__(self):
		return f"<MonsterAction(monster_id={self.monster_id}, name='{self.name}')>"

class MonsterTrait(Base):
	"""Специальные способности (Special Abilities / Traits) монстра"""
	__tablename__ = "monster_traits"
	id = Column(Integer, primary_key=True, index=True)
	monster_id = Column(Integer, ForeignKey('monsters.id', ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	description = Column(Text, nullable=False)
	monster = relationship("Monster", back_populates="traits")

	def __repr__(self):
		return f"<MonsterTrait(monster_id={self.monster_id}, name='{self.name}')>"

class Campaign(Base):
	"""Кампания (серия приключений)"""
	__tablename__ = "campaigns"
	id = Column(Integer, primary_key=True, index=True)
	owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	description = Column(Text, nullable=True)
	home_rules_json = Column(JSON, nullable=True)
	is_public = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

	owner = relationship("User")
	sessions = relationship("Session", back_populates="campaign", cascade="all, delete-orphan")
	characters = relationship("CampaignCharacter", back_populates="campaign")
	quests: Mapped[list["Quest"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
	locations: Mapped[list["Location"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")

	def __repr__(self):
		return f"<Campaign(name='{self.name}')>"

class Session(Base):
	"""Игровая сессия (одна встреча/вечер игры)"""
	__tablename__ = "sessions"
	id = Column(Integer, primary_key=True, index=True)
	campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
	date_played = Column(DateTime(timezone=True), nullable=False)
	summary = Column(Text, nullable=True)
	xp_distributed = Column(Integer, default=0)

	campaign = relationship("Campaign", back_populates="sessions")

	def __repr__(self):
		return f"<Session(date={self.date_played}, xp={self.xp_distributed})>"

class CampaignCharacter(Base):
	"""Связь персонажа и кампании (роль в кампании, статус, заметки)"""
	__tablename__ = "campaign_characters"
	campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
	role_in_campaign = Column(String(50), default="Player")
	joined_session = Column(Integer, nullable=True)
	notes = Column(Text, nullable=True)
	is_active = Column(Boolean(), default=True)

	campaign = relationship("Campaign", back_populates="characters")
	character = relationship("Character")

	def __repr__(self):
		return f"<CampaignCharacter(camp={self.campaign_id}, char={self.character_id}, role='{self.role_in_campaign}')>"

class Quest(Base):
	"""Квестовый движок. Хранит общую информацию о задании."""
	__tablename__ = "quests"
	id = Column(Integer, primary_key=True, index=True)
	campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
	location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
	issuer_faction_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
	title = Column(String(150), nullable=False)
	description = Column(Text, nullable=True)
	reward_xp = Column(Integer, default=0)
	reward_cp = Column(Integer, default=0)
	status = Column(String(20), default='active')
	created_at = Column(DateTime(timezone=True), server_default=func.now())

	campaign = relationship("Campaign", back_populates="quests")
	location = relationship("Location", back_populates="quests")
	issuer_faction = relationship("Organization")
	objectives: Mapped[list["QuestObjective"]] = relationship(
		back_populates="quest",
		cascade="all, delete-orphan",
		order_by="QuestObjective.order_num"
	)
	party_assignments: Mapped[list["PartyQuestAssignment"]] = relationship(back_populates="quest")

	def __repr__(self):
		return f"<Quest(title='{self.title}', status='{self.status}')>"

class QuestObjective(Base):
	"""Конкретная цель квеста: убить X, найти Y, поговорить с Z."""
	__tablename__ = "quest_objectives"
	id = Column(Integer, primary_key=True, index=True)
	quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True)
	order_num = Column(Integer, nullable=False)
	target_entity_type = Column(Enum(EntityTypeEnum), nullable=True)
	target_entity_name = Column(String(100), nullable=True)
	target_quantity = Column(Integer, default=1)
	is_completed = Column(Boolean(), default=False)
	quest = relationship("Quest", back_populates="objectives")

	def __repr__(self):
		return f"<QuestObj(quest={self.quest_id}, tgt='{self.target_entity_name} x{self.target_quantity}')>"

class PartyQuestAssignment(Base):
	"""Связь: какой персонаж или группа принял какой квест."""
	__tablename__ = "party_quest_assignments"
	id = Column(Integer, primary_key=True, index=True)
	quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)
	notes_dm = Column(Text, nullable=True)
	quest = relationship("Quest", back_populates="party_assignments")
	character = relationship("Character")

	def __repr__(self):
		return f"<PQAssign(quest={self.quest_id}, char={self.character_id})>"

class Location(Base):
	"""Локации (города, подземелья, комнаты) с поддержкой вложенности"""
	__tablename__ = "locations"
	id = Column(Integer, primary_key=True, index=True)
	campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
	name = Column(String(150), nullable=False)
	slug = Column(String(150), nullable=False, unique=True, index=True)
	parent_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
	location_type = Column(String(50), nullable=False)
	description = Column(Text, nullable=True)
	map_reference = Column(String(100), nullable=True)
	biome_type = Column(String(50), nullable=True)
	campaign = relationship("Campaign", back_populates="locations")
	parent = relationship("Location", remote_side=[id], backref="children")
	lore_entries: Mapped[list["LoreEntry"]] = relationship(back_populates="location")
	quests: Mapped[list["Quest"]] = relationship(back_populates="location")

	def __repr__(self):
		return f"<Location(name='{self.name}', type='{self.location_type}')>"

class NoteCategory(Base):
	"""Категории заметок (Lore, Quest, Character, NPC, Location)"""
	__tablename__ = "note_categories"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True)
	slug = Column(String(50), nullable=False, unique=True, index=True)
	color_hex = Column(String(7), nullable=True)

	def __repr__(self):
		return f"<NoteCategory(name='{self.name}')>"

class CharacterNote(Base):
	"""Заметки, привязанные к персонажу (личные, для игрока, для мастера)"""
	__tablename__ = "character_notes"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
	author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
	category_id = Column(Integer, ForeignKey("note_categories.id", ondelete="SET NULL"), nullable=True)
	title = Column(String(200), nullable=False)
	content = Column(Text, nullable=False)
	is_visible_to_player = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
	character = relationship("Character")
	author = relationship("User")
	category = relationship("NoteCategory")

	def __repr__(self):
		return f"<CharacterNote(title='{self.title}', char={self.character_id})>"

class CampaignNote(Base):
	"""Общие заметки по кампании (для мастера, лор, важные события)"""
	__tablename__ = "campaign_notes"
	id = Column(Integer, primary_key=True, index=True)
	campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
	author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
	category_id = Column(Integer, ForeignKey("note_categories.id", ondelete="SET NULL"), nullable=True)
	title = Column(String(200), nullable=False)
	content = Column(Text, nullable=False)
	sort_order = Column(SmallInteger, default=0)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	campaign = relationship("Campaign")
	author = relationship("User")
	category = relationship("NoteCategory")

	def __repr__(self):
		return f"<CampaignNote(title='{self.title}', camp={self.campaign_id})>"

class LoreEntry(Base):
	"""Запись в базе знаний (бестиарий, история дома Нозеров, описание ритуала)."""
	__tablename__ = "lore_entries"
	id = Column(Integer, primary_key=True, index=True)
	author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
	title = Column(String(150), nullable=False)
	content_text = Column(Text, nullable=True)
	entry_image_url = Column(String(255), nullable=True)
	tags_json = Column(JSON, nullable=True)
	is_public_to_party = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	author = relationship("User")
	location = relationship("Location", back_populates="lore_entries")

	def __repr__(self):
		return f"<LoreEntry(title='{self.title}', loc={self.location_id})>"