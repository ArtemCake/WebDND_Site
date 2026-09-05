# backend/app/models/content/equipment.py

"""Модели лора, языков и бестиария."""

from Config.imports import (Mapped, mapped_column, relationship, ARRAY, PG_UUID, uuid4,
						DateTime, datetime, String, Text, Boolean, ForeignKey, text,
						JSONB, Integer, Float, backref)
from backend.app.database.database import Base


# --- ЯЗЫКИ ---
class Language(Base):
	"""
	Справочник языков.
	Реализует требование ТЗ о хранении языков для рас и предысторий.
	"""
	__tablename__ = "languages"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Common', 'Elvish'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	script: Mapped[str | None] = mapped_column(String(50), nullable=True) # 'Common Script', 'Dwarvish Runes'
	is_standard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False) # True - базовый язык сеттинга

	is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Thieves' Cant, Druidic

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="languages") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_languages")

	races: Mapped[list["Race"]] = relationship(
		"Race", secondary="race_languages", back_populates="languages"
	)
	backgrounds: Mapped[list["Background"]] = relationship(
		"Background", secondary="background_languages", back_populates="languages"
	)
	origins: Mapped[list["Origin"]] = relationship(
		"Origin", secondary="origin_languages", back_populates="languages"
	)

	def __repr__(self) -> str:
		return f"<Language(id='{self.id}', name='{self.name}')>"

# --- БЕСТИАРИЙ ---
class Creature(Base):
	"""
	Справочник монстров и НПС.
	Реализует требование ТЗ о хранении бестиария с поддержкой Homebrew.
	"""
	__tablename__ = "bestiary"

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

	size_id: Mapped[int] = mapped_column(Integer, ForeignKey("creature_sizes.id"), nullable=False, index=True)
	type_id: Mapped[int] = mapped_column(Integer, ForeignKey("creature_types.id"), nullable=False, index=True)

	alignment: Mapped[str | None] = mapped_column(String(50), nullable=True) # e.g. 'Lawful Evil'

	armor_class: Mapped[int] = mapped_column(Integer, nullable=False)
	armor_type_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("armor_types.id"), nullable=True, index=True)

	hit_points: Mapped[int] = mapped_column(Integer, nullable=False)
	hit_dice: Mapped[str | None] = mapped_column(String(20), nullable=True) # e.g. '17d8+68'

	speed_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	# {"walk": 30, "fly": 60, "swim": 20, "climb": 10}

	ability_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	# {"str": 18, "dex": 14, "con": 16, "int": 8, "wis": 12, "cha": 7}

	saves_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	skills_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	vulnerabilities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
	resistances: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
	immunities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

	condition_immunities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

	senses_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	languages: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

	challenge_rating: Mapped[float] = mapped_column(Float, nullable=False) # e.g. 3.0, 1/2
	experience_reward: Mapped[int] = mapped_column(Integer, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="bestiary") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_creatures")
	size: Mapped["CreatureSize"] = relationship("CreatureSize")
	creature_type: Mapped["CreatureType"] = relationship("CreatureType")
	armor: Mapped["ArmorType"] = relationship("ArmorType")

	def __repr__(self) -> str:
		return f"<Creature(id='{self.id}', name='{self.name}', CR={self.challenge_rating})>"

# --- РАЗМЕРЫ СУЩЕСТВ ---
class CreatureSize(Base):
	"""
	Справочник размеров существ.
	Реализует требование ТЗ о хранении размеров как из бестиария, так и из рас.
	Влияет на занимаемое пространство (Space) и досягаемость (Reach).
	"""
	__tablename__ = "creature_sizes"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False) # e.g. 'Medium', 'Huge'
	slug: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

	abbreviation: Mapped[str] = mapped_column(String(5), unique=True, nullable=False) # M, L, H, G...

	space_feet: Mapped[int] = mapped_column(Integer, nullable=False) # Занимаемое пространство в футах (5x5, 10x10...)
	reach_feet: Mapped[int] = mapped_column(Integer, nullable=False) # Базовая досягаемость

	carrying_capacity_multiplier: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="creature_sizes") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_creature_sizes")
	creatures: Mapped[list["Creature"]] = relationship("Creature", back_populates="size", cascade="all, delete-orphan")
	races: Mapped[list["Race"]] = relationship("Race", back_populates="size", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<CreatureSize(id={self.id}, name='{self.name}', space={self.space_feet}')>"

# --- ТИПЫ СУЩЕСТВ ---
class CreatureType(Base):
	"""
	Справочник типов существ.
	Реализует требование ТЗ о хранении типов как из бестиария, так и из рас.
	Критически важен для работы заклинаний (например, 'Hold Person' работает только на Humanoid).
	"""
	__tablename__ = "creature_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Humanoid', 'Beast', 'Dragon'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="creature_types") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_creature_types")
	creatures: Mapped[list["Creature"]] = relationship("Creature", back_populates="creature_type", cascade="all, delete-orphan")
	races: Mapped[list["Race"]] = relationship("Race", back_populates="type", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<CreatureType(id={self.id}, name='{self.name}')>"

# --- НИП (НЕИГРОВЫЕ ПЕРСОНАЖИ) ---
class NPC(Base):
	"""
	Конкретные экземпляры НИП или божеств.
	Реализует требование ТЗ о хранении НПС, привязанных к лору мастера.
	В отличие от бестиария (шаблона), здесь хранятся конкретные статы и инвентарь персонажа.
	"""
	__tablename__ = "npcs"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	# Ссылка на шаблон из Бестиария (опционально, если НИ создан с нуля)
	creature_template_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("bestiary.id", ondelete="SET NULL"), nullable=True, index=True
	)

	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew/Лора Мастера
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	lore_entry_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("lore_entries.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)

	level: Mapped[int | None] = mapped_column(Integer, nullable=True) # Если НИ имеет классовый уровень
	alignment: Mapped[str | None] = mapped_column(String(50), nullable=True)

	armor_class: Mapped[int] = mapped_column(Integer, nullable=False)
	hit_points: Mapped[int] = mapped_column(Integer, nullable=False)

	ability_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	saves_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	skills_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_npcs")
	template: Mapped["Creature"] = relationship("Creature", foreign_keys=[creature_template_id])
	lore: Mapped["LoreEntry"] = relationship("LoreEntry")
	inventory: Mapped[list["CharacterInventory"]] = relationship(
		"CharacterInventory", back_populates="npc", cascade="all, delete-orphan"
	)
	tokens: Mapped[list["Token"]] = relationship("Token", back_populates="npc", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<NPC(id='{self.id}', name='{self.name}')>"

# --- ВИДЫ НПС ---
class NPCTag(Base):
	"""
	Справочник категорий/видов НПС.
	Реализует требование ТЗ о хранении видов НПС (разбойники, короли, божества и другие).
	Это тегирование для фильтрации и генерации случайных встреч.
	"""
	__tablename__ = "npc_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Bandit', 'Noble', 'Deity'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_divine: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Пометка для богов
	threat_level: Mapped[int | None] = mapped_column(Integer, nullable=True) # 1-20 для оценки силы энкаунтера

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="npc_types") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_npc_types")
	npcs: Mapped[list["NPC"]] = relationship(
		"NPC", secondary="npc_type_links", back_populates="types", cascade="all, delete"
	)

	def __repr__(self) -> str:
		return f"<NPCTag(id={self.id}, name='{self.name}')>"

# Ассоциативная таблица Многие-ко-многим между конкретными НИП и их видами/ролями
class NpcTypeLink(Base):
	__tablename__ = "npc_type_links"

	npc_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), primary_key=True
	)
	type_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("npc_types.id", ondelete="CASCADE"), primary_key=True
	)

# --- ЛОР ---
class LoreEntry(Base):
	"""
	Справочник лора мира мастера.
	Реализует требование ТЗ о хранении канонического и домашнего лора.
	Может содержать статьи о фракциях, истории мира или географии.
	"""
	__tablename__ = "lore_entries"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew/Лора Мастера
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	title: Mapped[str] = mapped_column(String(255), nullable=False)
	slug: Mapped[str] = mapped_column(String(255), nullable=False)

	content: Mapped[str] = mapped_column(Text, nullable=False) # Основной текст в Markdown/HTML

	entry_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'history', 'faction', 'geography', 'religion'

	parent_entry_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("lore_entries.id", ondelete="SET NULL"), nullable=True, index=True
	)

	tags_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, server_default="[]")
	# ['elvish_history', 'underdark', 'politics']

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="lore") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_lore")
	children: Mapped[list["LoreEntry"]] = relationship(
		"LoreEntry", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan"
	)
	npcs: Mapped[list["NPC"]] = relationship("NPC", back_populates="lore", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<LoreEntry(id='{self.id}', title='{self.title}')>"

