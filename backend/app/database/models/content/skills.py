# backend/app/models/content/skills.py

"""Модели характеристик и навыков персонажа."""

from Config.imports import (Mapped, mapped_column, relationship, ARRAY, ForeignKey, text,
					Text, String, Integer, Boolean, DateTime, PG_UUID, datetime, uuid4)
from backend.app.database.database import Base


# --- НАВЫКИ ---
class Skill(Base):
	"""
	Справочник навыков.
	Реализует требование ТЗ о жесткой привязке навыка к характеристике с возможностью Homebrew-изменения.
	"""
	__tablename__ = "skills"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g. 'Acrobatics', 'Stealth'
	slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	ability_score_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("characteristics.id", ondelete="RESTRICT"), nullable=False, index=True
	)

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="skills") # (нужно добавить в GameSystem)
	owner: Mapped["User"] = relationship("User", back_populates="created_skills")
	characteristic: Mapped["Characteristic"] = relationship("Characteristic", back_populates="skills")

	def __repr__(self) -> str:
		return f"<Skill(id='{self.id}', name='{self.name}')>"

# --- ХАРАКТЕРИСТИКИ ---
class Characteristic(Base):
	"""
	Базовые характеристики (Сила, Ловкость и т.д.).
	"""
	__tablename__ = "characteristics"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	abbreviation: Mapped[str] = mapped_column(String(3), unique=True, nullable=False) # STR, DEX, CON...
	full_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem", back_populates="characteristics") # (нужно добавить в GameSystem)
	skills: Mapped[list["Skill"]] = relationship("Skill", back_populates="characteristic", cascade="all, delete-orphan")
	sheets: Mapped[list["CharacterSheetAbilityScore"]] = relationship("CharacterSheetAbilityScore", back_populates="characteristic")

	def __repr__(self) -> str:
		return f"<Characteristic(id='{self.id}', abbr='{self.abbreviation}')>"

# --- КАРТА СВЯЗИ НАВЫКОВ И ХАРАКТЕРИСТИК (для Homebrew) ---
class SkillCharacteristicMap(Base):
	"""
	Промежуточная таблица для переопределения связи Навыка и Характеристики.
	Реализует требование ТЗ: "мастер может изменять каноничную связь...
	но такие изменения должны храниться в отдельных навыках с соответствующей пометкой".

	Если Мастер хочет, чтобы 'Скрытность' зависела от Мудрости вместо Ловкости,
	он создает запись здесь, которая имеет приоритет над стандартной связью skill.ability_score_id.
	"""
	__tablename__ = "skill_characteristic_map"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	# Для Homebrew
	owner_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	skill_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, unique=True
	)
	characteristic_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("characteristics.id", ondelete="RESTRICT"), nullable=False
	)

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	system: Mapped["GameSystem"] = relationship("GameSystem")
	owner: Mapped["User"] = relationship("User", back_populates="created_skill_char_maps")
	skill: Mapped["Skill"] = relationship("Skill", back_populates="custom_characteristic_link")
	characteristic: Mapped["Characteristic"] = relationship("Characteristic", back_populates="custom_skill_links")

	def __repr__(self) -> str:
		return f"<SkillCharMap(skill='{self.skill.name}', char='{self.characteristic.abbreviation}')>"

# Добавляем обратные связи в существующие модели внутри этого файла:
# В класс Skill (после определения характеристики):
Skill.custom_characteristic_link: Mapped[SkillCharacteristicMap | None] = relationship(
	"SkillCharacteristicMap", uselist=False, back_populates="skill", cascade="all, delete-orphan"
)

# В класс Characteristic:
Characteristic.custom_skill_links: Mapped[list[SkillCharacteristicMap]] = relationship(
	"SkillCharacteristicMap", back_populates="characteristic", cascade="all, delete-orphan"
)