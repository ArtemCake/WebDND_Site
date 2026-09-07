# backend/app/models/content/character_building.py

"""Модели билдинга персонажа: расы, классы, предыстории."""

from Config.imports import (DateTime, String, Text, Integer, Boolean, ForeignKey, Table, List,
	Mapped, mapped_column, relationship, JSONB, text, PG_UUID, ARRAY, datetime, uuid4, Column)
from backend.app.database.database import Base


race_languages = Table( "race_languages", Base.metadata,
                        Column("race_id", ForeignKey("races.id"), primary_key=True),
                        Column("language_id", ForeignKey("languages.id"), primary_key=True) )

# --- РАСЫ ---
class Race(Base):
	"""
	Справочник рас.
	Поддерживает как каноничный контент, так и Homebrew от мастеров.
	"""
	__tablename__ = "races"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	slug: Mapped[str] = mapped_column(String(100), nullable=False)  # Для URL

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	size_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("creature_sizes.id"), nullable=True)
	speed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30") # Базовая скорость в футах

	ability_bonuses: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	proficiencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True) # Владение навыками/инструментами
	languages: Mapped[List["Language"]] = relationship( back_populates="races", secondary="race_languages" )

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="races")
	owner: Mapped["User"] = relationship("User", back_populates="created_races")
	size: Mapped["CreatureSize"] = relationship("CreatureSize")
	creature_types: Mapped[List["CreatureType"]] = relationship( "CreatureType", secondary="creature_type_race_link", back_populates="races" )

	def __repr__(self) -> str:
		return f"<Race(id='{self.id}', name='{self.name}')>"

# --- КЛАССЫ ---
class CharacterClass(Base):
	"""
	Справочник классов персонажей и НПС.
	Поддерживает мультиклассирование через таблицу связей class_feature_links.
	"""
	__tablename__ = "classes"

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

	hit_die: Mapped[int] = mapped_column(Integer, nullable=False)  # Например, 8 для d8 у воина

	# Основная характеристика для расчета сложности заклинаний или маневров
	spellcasting_ability: Mapped[str | None] = mapped_column(String(20), nullable=True)

	# Владения по умолчанию при получении уровня в этом классе
	starting_proficiencies: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	saving_throw_proficiencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True) # e.g. ['strength', 'constitution']

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="classes")
	owner: Mapped["User"] = relationship("User", back_populates="created_classes")
	subclasses: Mapped[list["Subclass"]] = relationship("Subclass", back_populates="parent_class", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<CharacterClass(id='{self.id}', name='{self.name}')>"

# --- ПОДКЛАССЫ ---
class Subclass(Base):
	"""
	Специализация или архетип класса.
	Например: 'College of Lore' для Барда, 'Champion' для Воина.
	"""
	__tablename__ = "subclasses"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	# Прямая привязка к родительскому классу
	class_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
	)
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

	# Уровень, на котором персонаж получает этот подкласс (обычно 2-3 уровень в ДнД)
	level_unlock: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")

	features_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# Структура: {"level_3": {...}, "level_6": {...}} с описанием способностей

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	parent_class: Mapped["CharacterClass"] = relationship("CharacterClass", back_populates="subclasses")
	system: Mapped["GameSystem"] = relationship("GameSystem")
	owner: Mapped["User"] = relationship("User", back_populates="created_subclasses")

	def __repr__(self) -> str:
		return f"<Subclass(id='{self.id}', name='{self.name}', for_class_id='{self.class_id}')>"

# --- ПРЕДЫСТОРИИ ---
class Background(Base):
	"""
	Предыстория персонажа.
	Дает навыки, языки, инструменты и стартовое снаряжение.
	"""
	__tablename__ = "backgrounds"

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

	# Механика предыстории согласно ТЗ
	skill_proficiencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)  # e.g. ['insight', 'persuasion']
	tool_proficiencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)   # e.g. ['thieves_tools']
	language_ids: Mapped[list[PG_UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)

	feature_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
	feature_description: Mapped[str | None] = mapped_column(Text, nullable=True)

	starting_equipment: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# Структура: {"gp": 15, "items": [{"name": "Sack", "quantity": 1}]}

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="backgrounds") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_backgrounds")
	languages: Mapped[list["Language"]] = relationship(
		"Language", secondary="background_languages", back_populates="backgrounds"
	)

	def __repr__(self) -> str:
		return f"<Background(id='{self.id}', name='{self.name}')>"

# Ассоциативная таблица для связи Многие-ко-многим между Предысториями и Языками
# Позволяет одной предыстории давать несколько языков
class BackgroundLanguage(Base):
	__tablename__ = "background_languages"

	background_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("backgrounds.id", ondelete="CASCADE"), primary_key=True
	)
	language_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True
	)

# --- ЧЕРТЫ ---
class Feat(Base):
	"""
	Черта персонажа.
	Может быть выбрана вместо повышения характеристик при получении уровня.
	"""
	__tablename__ = "feats"

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

	# Механика черты
	ability_increase: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	# {"str": 1, "dex": 0} или null, если нет прироста

	prerequisites: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# Структура: {"ability_score": {"dex": 13}, "spellcasting": true, "race": ["elf"], "level": 4}

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="feats") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_feats")

	def __repr__(self) -> str:
		return f"<Feat(id='{self.id}', name='{self.name}')>"

# --- ПРОИСХОЖДЕНИЯ ---
class Origin(Base):
	"""
	Происхождение персонажа (D&D 2024).
	Объединяет в себе расу, предысторию и базовые владения.
	Для старых систем может использоваться как контейнер стартовых данных.
	"""
	__tablename__ = "origins"

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

	# Связи с базовыми справочниками
	race_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("races.id", ondelete="SET NULL"), nullable=True, index=True
	)
	background_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("backgrounds.id", ondelete="SET NULL"), nullable=True, index=True
	)

	# Механика происхождения
	ability_bonuses: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	proficiencies: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	starting_equipment: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	is_homebrew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	visibility_scope: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="origins") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_origins")
	race: Mapped["Race"] = relationship("Race")
	background: Mapped["Background"] = relationship("Background")
	lang_objects: Mapped[list["Language"]] = relationship(
		"Language", secondary="origin_languages", back_populates="origins"
	)
	languages: Mapped[List["Language"]] = relationship( back_populates="origins", secondary="origin_languages" )

	def __repr__(self) -> str:
		return f"<Origin(id='{self.id}', name='{self.name}')>"

# Ассоциативная таблица для языков происхождения
class OriginLanguage(Base):
	__tablename__ = "origin_languages"

	origin_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("origins.id", ondelete="CASCADE"), primary_key=True
	)
	language_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True
	)