# app/database/models.py

from Config.imports import (DateTime, func, SQLEnum, Enum, Float, UniqueConstraint,
	Column, Integer, String, Text, Boolean, ForeignKey, SmallInteger,
	relationship, Table, JSON, datetime)
from app.database.database import Base
from app.enums.db_enums import EntityTypeEnum
from app.enums.log_enums import LogLevelEnum, LogAction
from app.enums.user_enums import Role_enums
from app.enums.person_enums import (ItemCategory, ProtectionType, MagicItemRarity)


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

# Значения характеристик конкретного персонажа (связь с таблицей ability_types)
character_abilities = Table(
	'character_abilities',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ability_type_id', Integer, ForeignKey('ability_types.id'), primary_key=True),
	Column('score', SmallInteger, nullable=False, default=8),
	UniqueConstraint('character_id', 'ability_type_id', name='uq_character_ability')
)

# Владение навыками конкретным персонажем
skill_proficiencies = Table(
	'skill_proficiencies',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True),
	Column('is_expertise', Boolean(), default=False), # Экспертиза (двойной бонус)
	Column('proficient', Boolean(), default=True),   # Просто владение
	UniqueConstraint('character_id', 'skill_id', name='uq_character_skill')
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
	Column('is_attuned', Boolean(), default=False), # Для магических предметов
	Column('attunement_slots_used', SmallInteger, default=0),
	Column('equipped', Boolean(), default=False),
	UniqueConstraint('character_id', 'equipment_id', name='uq_character_equipment')
)

# Связь контроля: какой персонаж кем управляет (фамильяры, нежить, наемники)
character_allies = Table(
	'character_allies',
	Base.metadata,
	Column('owner_character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('ally_character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('control_type', String(20), nullable=False, default='summon'), # summon, companion, hireling
	Column('is_permanent', Boolean(), default=False),
	UniqueConstraint('owner_character_id', 'ally_character_id', name='uq_owner_ally')
)

# Вложенность предметов: что лежит внутри сумки или рюкзака
container_items = Table(
	'container_items',
	Base.metadata,
	Column('container_equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('item_equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('quantity', SmallInteger, nullable=False, default=1)
)

# Связь состояний: какие эффекты наложены на персонажа (Poisoned, Bless, Prone)
character_conditions = Table(
	'character_conditions',
	Base.metadata,
	Column('character_id', Integer, ForeignKey('characters.id', ondelete="CASCADE"), primary_key=True),
	Column('condition_id', Integer, ForeignKey('conditions.id'), primary_key=True),
	Column('source_character_id', Integer, ForeignKey('characters.id', ondelete="SET NULL"), nullable=True), # Кто наложил эффект
	Column('source_spell_id', Integer, ForeignKey('spells.id', ondelete="SET NULL"), nullable=True),
	Column('duration_type', String(20), default='instant'), # instant, turn, minute, hour, permanent
	Column('duration_value', Integer, nullable=True), # Например, число раундов или кубик (1d6+3)
	Column('remaining_duration', Integer, nullable=True),
	Column('concentration_required', Boolean(), default=False),
	Column('is_active', Boolean(), default=True),
	Column('stackable', Boolean(), default=False), # Можно ли накладывать дважды (Bless от разных кастеров не стакается)
	Column('applied_at', DateTime(timezone=True), server_default=func.now()),
	UniqueConstraint('character_id', 'condition_id', 'source_spell_id', name='uq_char_cond_source')
)

# Ассортимент магазинов: цена конкретного предмета у конкретного торговца
shop_inventory = Table(
	'shop_inventory',
	Base.metadata,
	Column('equipment_id', Integer, ForeignKey('equipment.id', ondelete="CASCADE"), primary_key=True),
	Column('price_cp', Integer, nullable=False) # Цена в медных монетах конкретно для этого торговца
)

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

	def __repr__(self):
		return f"<User(username='{self.username}', role='{self.role}')>"

# --- СПРАВОЧНИКИ СУЩНОСТЕЙ (Вариативные данные) ---

class AbilityType(Base):
	"""Типы характеристик (Сила, Ловкость, Удача, Мана и т.д.)"""
	__tablename__ = "ability_types"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True)
	slug = Column(String(50), nullable=False, unique=True, index=True)
	is_core = Column(Boolean(), default=False)
	description = Column(Text, nullable=True)
	character_abilities = relationship("CharacterAbilityValue", back_populates="type")
	skill_mappings = relationship("SkillAbilityMap", back_populates="ability_type")

	def __repr__(self):
		return f"<AbilityType(name='{self.name}', slug='{self.slug}')>"

class Skill(Base):
	"""Навыки (Скрытность, Акробатика, Магия)"""
	__tablename__ = "skills"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True)
	slug = Column(String(50), nullable=False, unique=True, index=True)
	description = Column(Text, nullable=True)
	proficiencies = relationship("SkillProficiency", back_populates="skill")
	mappings = relationship("SkillAbilityMap", back_populates="skill")

	def __repr__(self):
		return f"<Skill(name='{self.name}', slug='{self.slug}')>"

class SkillAbilityMap(Base):
	"""
	Связующая таблица: определяет, какая характеристика отвечает за какой навык.
	Позволяет Мастеру менять взаимосвязи (например, сделать 'Запугивание' от 'Удачи').
	"""
	__tablename__ = "skill_ability_map"
	skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
	ability_type_id = Column(Integer, ForeignKey("ability_types.id", ondelete="CASCADE"), primary_key=True)
	skill = relationship("Skill", back_populates="mappings")
	ability_type = relationship("AbilityType", back_populates="skill_mappings")

class Monster(Base):
	"""Блок статистики существа (Monster Stat Block)"""
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

	def __repr__(self):
		return f"<MonsterAction(monster_id={self.monster_id}, name='{self.name}')>"

class MonsterTrait(Base):
	"""Специальные способности (Special Abilities / Traits)"""
	__tablename__ = "monster_traits"
	id = Column(Integer, primary_key=True, index=True)
	monster_id = Column(Integer, ForeignKey('monsters.id', ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	description = Column(Text, nullable=False)
	monster = relationship("Monster", back_populates="traits")

	def __repr__(self):
		return f"<MonsterTrait(monster_id={self.monster_id}, name='{self.name}')>"

class Organization(Base):
	"""Организации (Гильдии воров, Арфисты, Культ Дракона)"""
	__tablename__ = "organizations"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	alignment_tendency = Column(String(20), nullable=True) # Lawful Evil, Chaotic Neutral
	description = Column(Text, nullable=True)
	members = relationship("Character", back_populates="organization")
	ranks = relationship("OrganizationRank", back_populates="organization", cascade="all, delete-orphan")

	def __repr__(self):
		return f"<Organization(name='{self.name}')>"

class OrganizationRank(Base):
	"""Ранги внутри организации для механики репутации"""
	__tablename__ = "organization_ranks"
	id = Column(Integer, primary_key=True, index=True)
	organization_id = Column(Integer, ForeignKey('organizations.id', ondelete="CASCADE"), nullable=False, index=True)
	rank_name = Column(String(50), nullable=False) # Initiate, Agent, Master
	required_reputation = Column(Integer, nullable=False, default=0)
	benefits_json = Column(JSON, nullable=True) # Доступ к товарам, бесплатное проживание
	organization = relationship("Organization", back_populates="ranks")

	def __repr__(self):
		return f"<OrgRank(org='{self.organization.name}', name='{self.rank_name}')>"

class ShopVendor(Base):
	"""Торговец или магазин"""
	__tablename__ = "shops"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	location_description = Column(Text, nullable=True)
	shop_type = Column(String(30), nullable=False) # General, Blacksmith, Alchemist, Magic
	inventory = relationship("Equipment", secondary=shop_inventory, lazy="select", backref="available_in_shops")

	def __repr__(self):
		return f"<Shop(name='{self.name}', type='{self.shop_type}')>"

# --- ДОМАШНИЕ ПРАВИЛА И НАБОРЫ ПРАВИЛ ---

class Ruleset(Base):
	__tablename__ = "rulesets"
	id = Column(Integer, primary_key=True, index=True)
	owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	is_public = Column(Boolean(), default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	characters = relationship("Character", back_populates="ruleset")
	owner = relationship("User", back_populates="rules_created", foreign_keys=[owner_id])

	def __repr__(self):
		return f"<Ruleset(id='{self.id}', name='{self.name}')>"

class HomebrewEntity(Base):
	__tablename__ = "homebrew_entities"
	id = Column(Integer, primary_key=True, index=True)
	creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	entity_type = Column(SQLEnum(EntityTypeEnum, literal_bindparam=True), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	parent_canon_id = Column(Integer, nullable=True)
	parent_canon_type = Column(SQLEnum(EntityTypeEnum, literal_bindparam=True), nullable=True)
	content_json = Column(JSON, nullable=False)
	approved_by_dm = Column(Boolean(), default=False)
	creator = relationship("User")
	parent_entity = relationship("Race", viewonly=True, overlaps="homebrew_variants")

	def __repr__(self):
		return f"<HomebrewEntity(type='{self.entity_type.value}', name='{self.name}')>"

# --- ОСНОВНАЯ СУЩНОСТЬ ПЕРСОНАЖА ---

class Character(Base):
	__tablename__ = "characters"
	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	ruleset_id = Column(Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True)
	name = Column(String(100), nullable=False)
	alignment = Column(String(20))
	experience_points = Column(Integer, default=0)
	proficiency_bonus = Column(SmallInteger, default=2)
	# Связи
	user = relationship("User", back_populates="characters")
	ruleset = relationship("Ruleset", back_populates="characters")
	classes = relationship("DnDClass", secondary=character_classes, backref="characters")
	spells = relationship("Spell", secondary=character_spells, backref="known_by")
	items = relationship("Item", secondary=character_items, backref="owners")
	# Связь с Предысторией
	background_id = Column(Integer, ForeignKey("backgrounds.id", ondelete="SET NULL"), nullable=True, index=True)
	background = relationship("Background", backref="characters")
	# Прямые отношения к данным характеристик и навыков
	abilities = relationship("CharacterAbilityValue", back_populates="character", lazy="joined")
	proficiencies = relationship("SkillProficiency", back_populates="character", lazy="joined")
	# Прямые отношения к новым таблицам
	known_languages = relationship("Language", secondary=character_languages, lazy="joined", backref="speakers")
	feats = relationship("Feat", secondary=character_feats, lazy="joined", backref="holders")
	equipment = relationship("Equipment", secondary=character_equipment, lazy="select", backref="carried_by")
	organization_id = Column(Integer, ForeignKey('organizations.id', ondelete="SET NULL"), nullable=True, index=True)
	organization = relationship("Organization", back_populates="members")

	# Отношение контроля над миньонами (Союзниками)
	controlled_allies = relationship("Character", secondary=character_allies,
		primaryjoin=(character_allies.c.owner_character_id == id),
		secondaryjoin=(character_allies.c.ally_character_id == id),
		lazy="select",
		backref="controller"
	)

	def __repr__(self):
		bg_name = self.background.name if self.background else "None"
		org_name = self.organization.name if self.organization else "None"
		return f"<Character(name='{self.name}', bg='{bg_name}', org='{org_name}')>"

# --- ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ ДАННЫХ ПЕРСОНАЖА ---

class CharacterAbilityValue(Base):
	"""
	Конкретное значение характеристики у персонажа.
	Отдельная модель вместо связи внутри таблицы 'characters' для гибкости.
	"""
	__tablename__ = "character_abilities_values"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
	ability_type_id = Column(Integer, ForeignKey("ability_types.id"), nullable=False, index=True)
	score = Column(SmallInteger, nullable=False, default=8)
	character = relationship("Character", back_populates="abilities")
	type = relationship("AbilityType", back_populates="character_abilities")
	__table_args__ = (
		UniqueConstraint('character_id', 'ability_type_id', name='uq_char_ability_val'),
	)

	def __repr__(self):
		return f"<CharAbility(char_id={self.character_id}, abil='{self.type.slug}', val={self.score})>"

class SkillProficiency(Base):
	__tablename__ = "character_skill_proficiencies"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
	skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
	is_expertise = Column(Boolean(), default=False)
	proficient = Column(Boolean(), default=True)
	character = relationship("Character", back_populates="proficiencies")
	skill = relationship("Skill", back_populates="proficiencies")
	__table_args__ = (
		UniqueConstraint('character_id', 'skill_id', name='uq_char_skill_prof'),
	)

	def __repr__(self):
		status = "Expert" if self.is_expertise else ("Yes" if self.proficient else "No")
		return f"<SkillProf(char_id={self.character_id}, skill='{self.skill.slug}', prof={status})>"

# --- КЛАССЫ, РАСЫ, ЗАКЛИНАНИЯ, ПРЕДМЕТЫ ---

class Race(Base):
	__tablename__ = "races"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	size = Column(String(20), nullable=False)
	speed = Column(SmallInteger, nullable=False, default=30)
	stats_modifiers = Column(JSON)
	darkvision_range = Column(SmallInteger, nullable=True)
	languages = Column(JSON, nullable=True)
	homebrew_variants = relationship("HomebrewEntity", back_populates="parent_entity", foreign_keys="HomebrewEntity.parent_canon_id")

	def __repr__(self):
		return f"<Race(name='{self.name}')>"

class DnDClass(Base):
	__tablename__ = "classes"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	hit_die = Column(SmallInteger, nullable=False)
	saving_throw_proficiencies = Column(JSON, nullable=False)
	subclasses = relationship("Subclass", back_populates="dnd_class")
	homebrew_variants = relationship("HomebrewEntity", back_populates="parent_entity", foreign_keys="HomebrewEntity.parent_canon_id")

	def __repr__(self):
		return f"<DnDClass(name='{self.name}')>"

class Subclass(Base):
	__tablename__ = "subclasses"
	id = Column(Integer, primary_key=True, index=True)
	class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	level_unlock = Column(SmallInteger, nullable=False, default=3)
	dnd_class = relationship("DnDClass", back_populates="subclasses")

	def __repr__(self):
		return f"<Subclass(name='{self.name}', class_id='{self.class_id}')>"

class Spell(Base):
	__tablename__ = "spells"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	level = Column(SmallInteger, nullable=False, default=0)
	school = Column(String(50), nullable=False)
	casting_time = Column(String(50))
	range_val = Column(String(50))
	components = Column(JSON, nullable=False)
	duration = Column(String(50))
	damage = Column(JSON, nullable=True)

	def __repr__(self):
		return f"<Spell(name='{self.name}', lvl='{self.level}')>"

class Item(Base):
	__tablename__ = "items"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False)
	# Использование ENUM из person_enums.py для строгой типизации категорий предметов в БД
	category = Column(SQLEnum(ItemCategory, literal_bindparam=True), nullable=False, index=True)
	weight = Column(Float, nullable=True)
	cost_cp = Column(Integer, default=0)
	# Использование ENUM для типов защиты/резистов
	protection_type = Column(SQLEnum(ProtectionType, literal_bindparam=True), nullable=True)
	description = Column(Text, nullable=True)
	properties = Column(JSON, nullable=True)
	magic_item_data = relationship("MagicItem", uselist=False, back_populates="item", cascade="all, delete-orphan")

	def __repr__(self):
		return f"<Item(name='{self.name}', category='{self.category.value if self.category else None}')>"

class Language(Base):
	"""Справочник языков"""
	__tablename__ = "languages"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True) # Common, Elvish, Draconic
	script = Column(String(50), nullable=True)
	type = Column(String(20), nullable=True)
	characters = relationship("Character", secondary=character_languages, backref="known_languages")

	def __repr__(self):
		return f"<Language(name='{self.name}')>"

class Background(Base):
	"""Предыстория персонажа"""
	__tablename__ = "backgrounds"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	skill_proficiencies = Column(JSON, nullable=False) # ["insight", "persuasion"]
	tool_proficiencies = Column(JSON, nullable=True)
	languages = Column(JSON, nullable=True)
	feature_name = Column(String(100), nullable=False)
	feature_description = Column(Text, nullable=True)
	suggested_traits = Column(JSON, nullable=True)

	def __repr__(self):
		return f"<Background(name='{self.name}')>"

class Feat(Base):
	"""Черта (Feat)"""
	__tablename__ = "feats"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(100), nullable=False, unique=True)
	prerequisites = Column(JSON, nullable=True)
	summary = Column(Text, nullable=True)
	benefit = Column(Text, nullable=False)
	source_book = Column(String(50), nullable=True)
	characters = relationship("Character", secondary=character_feats, backref="feats")

	def __repr__(self):
		return f"<Feat(name='{self.name}')>"

class EquipmentSlot(Base):
	"""Слоты для экипировки (слот оружия, слот брони, кольца и т.д.)"""
	__tablename__ = "equipment_slots"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True) # Main Hand, Armor, Ring
	slot_type = Column(String(20), nullable=False) # weapon, armor, clothing, ring, feet
	max_items = Column(SmallInteger, nullable=False, default=1)
	equipment = relationship("Equipment", back_populates="slot")

	def __repr__(self):
		return f"<EquipmentSlot(name='{self.name}', type='{self.slot_type}')>"

class MagicItem(Base):
	"""Магический предмет. Наследует базовые поля от обычного предмета через связь."""
	__tablename__ = "magic_items"
	id = Column(Integer, primary_key=True, index=True)
	item_id = Column(Integer, ForeignKey('items.id', ondelete="CASCADE"), nullable=False, unique=True)
	requires_attunement = Column(Boolean(), default=False)
	attunement_by_class = Column(JSON, nullable=True) # ["wizard", "warlock"]
	attunement_by_race = Column(JSON, nullable=True)  # ["elf", "dwarf"]
	rarity = Column(SQLEnum(MagicItemRarity, literal_bindparam=True), nullable=False, default=MagicItemRarity.COMMON)
	description = Column(Text, nullable=True)
	resale_value_modifier = Column(Float, default=1.0) # Множитель стоимости при продаже
	item = relationship("Item", back_populates="magic_item_data")

	def __repr__(self):
		return f"<MagicItem(item_name='{self.item.name}', rarity='{self.rarity.value}')>"

class Equipment(Base):
	"""
	Конкретный экземпляр экипировки у персонажа или в магазине.
	Это связующее звено между общим справочником Items и конкретным персонажем.
	Позволяет хранить состояние (прочность, заряды).
	"""
	__tablename__ = "equipment"
	id = Column(Integer, primary_key=True, index=True)
	character_id = Column(Integer, ForeignKey('characters.id', ondelete="SET NULL"), nullable=True, index=True)
	item_id = Column(Integer, ForeignKey('items.id', ondelete="CASCADE"), nullable=False, index=True)
	slot_id = Column(Integer, ForeignKey('equipment_slots.id'), nullable=True, index=True)
	current_durability = Column(SmallInteger, nullable=True) # Прочность (для оружия/брони)
	charges = Column(SmallInteger, nullable=True)            # Заряды (для жезлов)
	is_identified = Column(Boolean(), default=False)         # Опознано ли свойство магии
	slot = relationship("EquipmentSlot", back_populates="equipment")
	item = relationship("Item", backref="equipment_instances")
	parent_container_id = Column(Integer, ForeignKey('equipment.id', ondelete="SET NULL"), nullable=True, index=True)
	capacity_weight = Column(Float, nullable=True) # Лимит веса в кг/фунтах
	contained_items = relationship("Equipment", secondary=container_items,
		primaryjoin=(id == container_items.c.container_equipment_id),
		secondaryjoin=(id == container_items.c.item_equipment_id),
		lazy="select", backref="parent_container")
	slot = relationship("EquipmentSlot", back_populates="equipment")
	item = relationship("Item", back_populates="equipment_instances")

	def __repr__(self):
		owner = f"char_id={self.character_id}" if self.character_id else "storage"
		return f"<Equip(id={self.id}, item='{self.item.name}', owner={owner})>"

class Condition(Base):
	"""Состояния (Blinded, Poisoned, Prone, Invisible) и магические эффекты"""
	__tablename__ = "conditions"
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False, unique=True) # Stunned, Charmed, Bless
	slug = Column(String(50), nullable=False, unique=True, index=True)
	description = Column(Text, nullable=True)
	mechanical_effects_json = Column(JSON, nullable=True)
	# Пример структуры: {"disadvantage_attack": true, "speed_0": true, "ac_bonus": 2}
	applied_to = relationship("Character", secondary=character_conditions, backref="active_conditions")

	def __repr__(self):
		return f"<Condition(name='{self.name}', slug='{self.slug}')>"
