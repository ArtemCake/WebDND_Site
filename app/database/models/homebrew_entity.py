from Config.imports import (
	DateTime, func, SQLEnum, Integer, String, Boolean, ForeignKey,
	relationship, JSON, datetime, Mapped, mapped_column, backref, select, and_, or_)
from app.database.database import Base
from app.database.models.dnd import Race, Class_, Background, Item, Spell
from app.enums.db_enums import EntityTypeEnum


class HomebrewEntity(Base):
	"""
	Базовая сущность для любого кастомного контента.
	Позволяет переопределять официальные книги (PHB, DMG) или добавлять
	абсолютно новые сущности через систему патчей.
	"""
	__tablename__ = "homebrew_entities"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	creator_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
	)

	ruleset_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), index=True,
		comment="Если задан, модификатор активен только в этом наборе правил"
	)

	entity_type: Mapped[EntityTypeEnum] = mapped_column(
		SQLEnum(EntityTypeEnum, native_enum=True, create_constraint=False),
		nullable=False,
		index=True,
		comment="Тип базовой сущности (RACE, CLASS, ITEM и т.д.)"
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

	# Ссылка на оригинальную запись из базы данных (для редактирования/наследования)
	parent_canon_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
	parent_canon_type: Mapped[EntityTypeEnum | None] = mapped_column(
		SQLEnum(EntityTypeEnum, native_enum=True, create_constraint=False), nullable=True
	)

	# Основное хранилище данных хоумбрю-контента
	freeform_content: Mapped[dict | None] = mapped_column(JSON, nullable=True,
	                                                      comment="Произвольный JSON с описанием (flavor text, biography)"
	                                                      )

	rules_patch: Mapped[dict | None] = mapped_column(JSON, nullable=True,
	                                                 comment="JSON-патч для изменения формул (например, {\"hp_formula\": \"...\"})"
	                                                 )

	is_approved: Mapped[bool] = mapped_column(Boolean(), default=False,
	                                          comment="Флаг премодерации администратором"
	                                          )
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

	# --- СВЯЗИ ---

	creator: Mapped["User"] = relationship("User", back_populates="homebrew_entities")

	ruleset: Mapped["Ruleset | None"] = relationship(
		"Ruleset",
		back_populates="homebrew_entities",
		foreign_keys=[ruleset_id],
		passive_deletes=True
	)

	# Полиморфная связь обратно к канонической сущности
	# ИСПРАВЛЕНО: Используем .select() со строковыми путями к таблицам для избежания циклических импортов при компиляции Mapper'а
	parent_entity: Mapped["Race | Class_ | Background | Item | Spell | None"] = relationship(
		viewonly=True,
		lazy="raise",
		foreign_keys=[parent_canon_id],

		# Явно задаем join по ID и типу, используя абсолютные пути к таблицам моделей
		primaryjoin=lambda: or_(
			and_(
				HomebrewEntity.parent_canon_id == select(Race).where(Race.id == HomebrewEntity.parent_canon_id).correlate_except(HomebrewEntity),
				HomebrewEntity.parent_canon_type == 'app.enums.db_enums.EntityTypeEnum.RACE'
			),
			and_(
				HomebrewEntity.parent_canon_id == select(Class_).where(Class_.id == HomebrewEntity.parent_canon_id).correlate_except(HomebrewEntity),
				HomebrewEntity.parent_canon_type == 'app.enums.db_enums.EntityTypeEnum.CLASS'
			),
			and_(
				HomebrewEntity.parent_canon_id == select(Background).where(Background.id == HomebrewEntity.parent_canon_id).correlate_except(HomebrewEntity),
				HomebrewEntity.parent_canon_type == 'app.enums.db_enums.EntityTypeEnum.BACKGROUND'
			),
			and_(
				HomebrewEntity.parent_canon_id == select(Item).where(Item.id == HomebrewEntity.parent_canon_id).correlate_except(HomebrewEntity),
				HomebrewEntity.parent_canon_type == 'app.enums.db_enums.EntityTypeEnum.ITEM'
			),
			and_(
				HomebrewEntity.parent_canon_id == select(Spell).where(Spell.id == HomebrewEntity.parent_canon_id).correlate_except(HomebrewEntity),
				HomebrewEntity.parent_canon_type == 'app.enums.db_enums.EntityTypeEnum.SPELL'
			),
		),
		doc="Ссылка на объект оригинальной книги, который мы перезаписываем"
	)

	# Связь вариантов (версионность): кто заменяет текущий хоумбрю-объект
	child_variants: Mapped[list["HomebrewEntity"]] = relationship(
		"HomebrewEntity",
		remote_side=[id],
		backref=backref("parent_variant", remote_side=[parent_canon_id]),
		cascade="all, delete-orphan",
		passive_deletes=True,
		doc="Список новых версий этого же объекта"
	)

	def __repr__(self) -> str:
		status = "Active" if self.is_active else "Disabled"
		approval = " [APPROVED]" if self.is_approved else ""
		return (
			f"<HomebrewEntity(id={self.id}, v{self.version}, type='{self.entity_type.value}', "
			f"name='{self.name}'{approval}, status='{status}')>"
		)