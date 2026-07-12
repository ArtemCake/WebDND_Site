from Config.imports import (
	DateTime, func, SQLEnum, Enum, CheckConstraint,
	Column, Integer, String, Text, Boolean, ForeignKey, SmallInteger,
	relationship, Table, JSON, UniqueConstraint, datetime
)
from app.database.database import Base
from app.enums.log_enums import LogLevelEnum, LogAction
from app.enums.person_enums import ItemCategory, ProtectionType, PreparationStatus, ProficiencyType
from app.enums.user_enums import Role_enums


# --- АССОЦИАТИВНЫЕ ТАБЛИЦЫ ---

race_languages = Table(
	"race_languages",
	Base.metadata,
	Column("race_id", Integer, ForeignKey("races.id", ondelete="CASCADE"), primary_key=True),
	# Было: language_name, стало: language_id
	Column("language_id", Integer, ForeignKey("languages.id"), primary_key=True)
)

race_ability_bonuses = Table(
	"race_ability_bonuses",
	Base.metadata,
	Column("race_id", Integer, ForeignKey("races.id", ondelete="CASCADE"), primary_key=True),
	Column("ability_id", Integer, ForeignKey("abilities.id"), primary_key=True),
	Column("bonus_value", Integer, nullable=False, default=2)
)

class_proficiencies = Table(
	"class_proficiencies",
	Base.metadata,
	Column("class_id", Integer, ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True),
	Column("proficiency_id", Integer, ForeignKey("proficiencies.id"), primary_key=True)
)

class_saving_throws = Table(
	"class_saving_throws",
	Base.metadata,
	Column("class_id", Integer, ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True),
	Column("ability_id", Integer, ForeignKey("abilities.id"), primary_key=True)
)

character_skills = Table(
	"character_skills",
	Base.metadata,
	Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
	Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
	Column("is_proficient", Boolean, nullable=False, default=False),
	Column("is_expertise", Boolean, nullable=False, default=False)
)

saving_throws = Table(
	"saving_throws",
	Base.metadata,
	Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
	Column("ability_id", Integer, ForeignKey("abilities.id"), primary_key=True),
	Column("is_proficient", Boolean, nullable=False, default=False)
)

character_inventory = Table(
	"character_inventory",
	Base.metadata,
	Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
	Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
	Column("quantity", Integer, nullable=False, default=1),
	Column("is_equipped", Boolean, nullable=False, default=False),
	Column("slot", String(50)),
	UniqueConstraint("character_id", "item_id", "slot", name="uq_char_inv_slot")
)

character_spells = Table(
	"character_spells",
	Base.metadata,
	Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
	Column("spell_id", Integer, ForeignKey("spells.id"), primary_key=True),
	Column("preparation_status", SQLEnum(PreparationStatus, literal_bindparam=True), nullable=False, default='known'),
	Column("notes", Text)
)

character_feats = Table(
	"character_feats",
	Base.metadata,
	Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
	Column("feat_id", Integer, ForeignKey("feats.id"), primary_key=True),
	Column("notes", Text)
)

# Теперь это ассоциативная таблица к DamageType, а не просто строки
damage_protection_assoc = Table(
	"damage_resistances_vulnerabilities",
	Base.metadata,
	Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
	Column("damage_type_id", Integer, ForeignKey("damage_types.id"), primary_key=True),
	Column("protection_type", SQLEnum(ProtectionType, literal_bindparam=True), nullable=False),
	Column("source", String(100)),
	Column("source_detail", String(255))
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
		return f"<user_logs(user_id='{self.user_id}', log_level='{self.log_level}')>"

class AppLog(Base):
	__tablename__ = "app_logs"
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(50), nullable=True, index=True)
	action = Column(SQLEnum(LogAction, literal_bindparam=True), nullable=False, index=True)
	description = Column(Text, nullable=True)
	timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
	log_level = Column(SQLEnum(LogLevelEnum, literal_bindparam=True), nullable=False, default=LogLevelEnum.INFO, index=True)

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

	def __repr__(self):
		return f"<User(username='{self.username}', role='{self.role}')>"

class Ability(Base):
	__tablename__ = "abilities"
	id = Column(Integer, primary_key=True)
	name = Column(String(50), unique=True, nullable=False)  # Strength, Dexterity, etc.
	abbreviation = Column(String(3), unique=True, nullable=False)  # STR, DEX
	description = Column(Text)

	character_saving_throws = relationship("Character", secondary=saving_throws, back_populates="saving_throws")
	races = relationship("Race", secondary=race_ability_bonuses, back_populates="ability_bonuses")
	class_sources = relationship("CharClass", secondary=class_saving_throws, back_populates="saving_throws")

class Size(Base):
	__tablename__ = "sizes"
	id = Column(Integer, primary_key=True)
	name = Column(String(50), unique=True, nullable=False)
	space = Column(Integer, default=5)

class Language(Base):
	__tablename__ = "languages"
	# Было: name = Column(String(50), primary_key=True)
	id = Column(Integer, primary_key=True)
	name = Column(String(50), unique=True, nullable=False)
	script = Column(String(50))

	# Если нужно, можно добавить обратную связь к расам:
	races = relationship("Race", secondary=race_languages, back_populates="languages")

class Race(Base):
	__tablename__ = "races"
	id = Column(Integer, primary_key=True)
	name = Column(String(100), unique=True, nullable=False)
	size_id = Column(Integer, ForeignKey("sizes.id"))
	speed = Column(SmallInteger, nullable=False, default=30)
	alignment_tendency = Column(String(50))
	traits_description = Column(Text)

	languages = relationship("Language", secondary=race_languages, back_populates="races")
	ability_bonuses = relationship("Ability", secondary=race_ability_bonuses, back_populates="races")
	traits = relationship("Trait", back_populates="source_race")
	subraces = relationship("Subrace", back_populates="parent_race")

class Subrace(Base):  # Только для подрас (не подклассы)
	__tablename__ = "subraces"
	id = Column(Integer, primary_key=True)
	name = Column(String(100), nullable=False)
	parent_race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
	additional_traits = Column(Text)
	level_granted = Column(Integer, default=0)

	parent_race = relationship("Race", back_populates="subraces")

class CharClass(Base):
	__tablename__ = "classes"
	id = Column(Integer, primary_key=True)
	name = Column(String(100), unique=True, nullable=False)
	hit_die = Column(String(10), nullable=False)  # d8, d10
	primary_ability_id = Column(Integer, ForeignKey("abilities.id"))

	proficiencies = relationship("Proficiency", secondary=class_proficiencies, back_populates="classes")
	saving_throws = relationship("Ability", secondary=class_saving_throws, back_populates="class_sources")
	features = relationship("Feature", back_populates="source_class")
	levels = relationship("ClassLevel", back_populates="char_class", cascade="all, delete-orphan")

class ClassLevel(Base):
	__tablename__ = "class_levels"
	__table_args__ = (
		CheckConstraint("level BETWEEN 1 AND 20", name="ck_class_level_range"),
		UniqueConstraint("class_id", "level", name="uq_class_level"),
	)
	id = Column(Integer, primary_key=True)
	class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
	level = Column(SmallInteger, nullable=False)
	proficiency_bonus = Column(SmallInteger, nullable=False)
	features_json = Column(JSON, nullable=False)
	spell_slots = Column(JSON)

	char_class = relationship("CharClass", back_populates="levels")

class Proficiency(Base):
	__tablename__ = "proficiencies"
	id = Column(Integer, primary_key=True)
	name = Column(String(100), unique=True, nullable=False)
	proficiency_type = Column(SQLEnum(ProficiencyType, literal_bindparam=True), nullable=False)

	classes = relationship("CharClass", secondary=class_proficiencies, back_populates="proficiencies")

class Background(Base):
	__tablename__ = "backgrounds"
	id = Column(Integer, primary_key=True)
	name = Column(String(100), unique=True, nullable=False)
	feature_name = Column(String(100))
	feature_description = Column(Text)
	skill_choices_count = Column(Integer, nullable=False, default=2)
	tool_choices_count = Column(Integer, default=0)
	language_choices_count = Column(Integer, default=0)

class Skill(Base):
	__tablename__ = "skills"
	id = Column(Integer, primary_key=True)
	name = Column(String(100), unique=True, nullable=False)
	ability_check_id = Column(Integer, ForeignKey("abilities.id"), nullable=False)
	description = Column(Text)
	has_armor_penalty = Column(Boolean, default=False)
	characters = relationship(
		"Character",
		secondary=character_skills,
		back_populates="skills"
	)

	ability = relationship("Ability")

class DamageType(Base):
	__tablename__ = "damage_types"
	id = Column(Integer, primary_key=True)
	name_en = Column(String(50), unique=True, nullable=False)
	name_ru = Column(String(50))
	description = Column(Text)

	protected_characters = relationship(
		"Character",
		secondary=damage_protection_assoc,
		back_populates="damage_protections"
	)

class Feature(Base):
	__tablename__ = "features"
	id = Column(Integer, primary_key=True)
	name = Column(String(150), nullable=False)
	source_type = Column(String(50), nullable=False)  # race, subclass, class, background
	source_id = Column(Integer, nullable=False)
	description = Column(Text)
	order = Column(Integer, default=0)

	char_class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
	source_class = relationship("CharClass", back_populates="features")

class Trait(Base):
	__tablename__ = "traits"
	id = Column(Integer, primary_key=True)
	name = Column(String(150), nullable=False)
	source_race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
	description = Column(Text)

	source_race = relationship("Race", back_populates="traits")

class Feat(Base):
	__tablename__ = "feats"
	id = Column(Integer, primary_key=True)
	name = Column(String(150), unique=True, nullable=False)
	prerequisites = Column(Text)  # требования к черте (например, STR 13)
	description = Column(Text)

class Item(Base):
	__tablename__ = "items"
	id = Column(Integer, primary_key=True)
	name = Column(String(150), nullable=False)
	category = Column(SQLEnum(ItemCategory, literal_bindparam=True), nullable=False)
	weight = Column(SmallInteger, default=1)
	value_copper = Column(Integer, default=0)
	description = Column(Text)

class Spell(Base):
	__tablename__ = "spells"
	id = Column(Integer, primary_key=True)
	name = Column(String(150), nullable=False)
	level = Column(SmallInteger, default=0)          # 0 = кантрипы
	school = Column(String(50))
	casting_time = Column(String(50))
	range = Column(String(50))
	duration = Column(String(50))
	components = Column(String(20))                 # VSM
	description = Column(Text)

class Character(Base):
	__tablename__ = "characters"
	__table_args__ = (
		CheckConstraint("current_level BETWEEN 1 AND 20", name="ck_char_level_range"),
		CheckConstraint("strength BETWEEN 3 AND 30", name="ck_char_strength"),
		CheckConstraint("dexterity BETWEEN 3 AND 30", name="ck_char_dexterity"),
		CheckConstraint("constitution BETWEEN 3 AND 30", name="ck_char_constitution"),
		CheckConstraint("intelligence BETWEEN 3 AND 30", name="ck_char_intelligence"),
		CheckConstraint("wisdom BETWEEN 3 AND 30", name="ck_char_wisdom"),
		CheckConstraint("charisma BETWEEN 3 AND 30", name="ck_char_charisma"),
	)

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(150), nullable=False)
	player_name = Column(String(150))

	race_id = Column(Integer, ForeignKey("races.id"))
	subrace_id = Column(Integer, ForeignKey("subraces.id"))
	class_id = Column(Integer, ForeignKey("classes.id"))
	background_id = Column(Integer, ForeignKey("backgrounds.id"))

	current_level = Column(SmallInteger, default=1)
	alignment = Column(String(50))
	personality_trait = Column(Text)
	ideal = Column(Text)
	bond = Column(Text)
	flaw = Column(Text)
	backstory_summary = Column(Text)

	strength = Column(SmallInteger, default=10)
	dexterity = Column(SmallInteger, default=10)
	constitution = Column(SmallInteger, default=10)
	intelligence = Column(SmallInteger, default=10)
	wisdom = Column(SmallInteger, default=10)
	charisma = Column(SmallInteger, default=10)

	user = relationship("User", back_populates="characters")
	race = relationship("Race")
	subrace = relationship("Subrace")
	char_class = relationship("CharClass")

	skills = relationship(
		"Skill",
		secondary=character_skills,
		back_populates="characters",  # нужно будет добавить в Skill
		collection_class=list
	)
	saving_throws = relationship(
		"Ability",
		secondary=saving_throws,
		back_populates="character_saving_throws"  # нужно будет добавить в Ability
	)
	damage_protections = relationship(
		"DamageType",
		secondary=damage_protection_assoc,
		back_populates="protected_characters"
	)