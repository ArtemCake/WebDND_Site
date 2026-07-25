# app/database/models/core.py

from Config.imports import (
	DateTime, func, UniqueConstraint, CheckConstraint,
	Integer, String, Text, Boolean, ForeignKey, SmallInteger,
	relationship, JSON, datetime, Mapped, mapped_column)
from app.database.database import Base


class CalculationField(Base):
	"""
	Справочник всех динамически рассчитываемых полей персонажа или существа.
	Позволяет правилам ссылаться на конкретные данные по ID/пути, а не по строке.
	Аналог "Source/Destination" из D&D Beyond.
	"""
	__tablename__ = "calculation_fields"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	entity_type: Mapped[str] = mapped_column(String(50), nullable=False,
	                                         comment="К какой сущности относится поле (Character, Monster, Item)")
	field_path: Mapped[str] = mapped_column(String(100), nullable=False, unique=True,
	                                        comment="JSONPath или dot-нотация до поля (например, stats.strength.score)")
	display_name: Mapped[str] = mapped_column(String(100), nullable=False,
	                                          comment="Человекочитаемое имя для интерфейса")
	data_type: Mapped[str] = mapped_column(String(20), nullable=False,
	                                       comment="Тип данных: int, float, bool, string")
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Обратная связь ко всем модификаторам, влияющим на это поле
	modifiers: Mapped[list["RulesetModifier"]] = relationship(
		back_populates="target_field",
		cascade="all, delete-orphan"
	)

	def __repr__(self) -> str:
		return f"<CalculationField(path='{self.field_path}', name='{self.display_name}')>"

class RulesetModifier(Base):
	"""
	Модификатор правила. Узел вычислительного графа.
	Определяет КАК меняется конкретное поле (CalculationField).
	"""
	__tablename__ = "ruleset_modifiers"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	ruleset_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("rulesets.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
		comment="ID набора правил, которому принадлежит узел"
	)

	calculation_field_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("calculation_fields.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
		comment="На какое поле влияет этот модификатор"
	)

	depends_on_modifier_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("ruleset_modifiers.id", ondelete="SET NULL"),
		nullable=True,
		index=True,
		comment="Зависимость от другого узла графа (для цепочек вычислений)"
	)

	priority: Mapped[int] = mapped_column(SmallInteger, default=100, nullable=False,
	                                      comment="Порядок выполнения. Меньшее значение выполняется раньше.")

	modifier_type: Mapped[str] = mapped_column(String(30), nullable=False,
	                                           comment="Тип операции: set_value, add_bonus, multiply_multiplier")

	config_json: Mapped[dict] = mapped_column(JSON, nullable=False,
	                                          comment="Параметры модификатора (значение, кости кубика, условие)")

	condition_json: Mapped[dict | None] = mapped_column(JSON, nullable=True,
	                                                    comment="Условие активации (если null — действует всегда)")

	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

	# --- Связи ---
	ruleset: Mapped["Ruleset"] = relationship(back_populates="modifiers")
	target_field: Mapped["CalculationField"] = relationship(back_populates="modifiers")

	# Рекурсивная связь для построения дерева зависимостей
	depends_on: Mapped["RulesetModifier | None"] = relationship(
		remote_side=[id],
		backref="dependent_modifiers",
		post_update=True # Важно для избежания циклического flush при CASCADE
	)

	__table_args__ = (
		# Правило должно быть уникальным внутри одного набора правил для конкретного поля и приоритета
		CheckConstraint(
			"priority >= 0",
			name="ck_modifier_priority_non_negative"
		),
		# Уникальность позиции в графе
		{"schema": None}
	)

	__table_args__ = (
		UniqueConstraint('ruleset_id', 'calculation_field_id', 'priority', name='uq_ruleset_field_priority'),
		CheckConstraint("priority >= 0", name="ck_modifier_priority_non_negative"),
	)

	def __repr__(self) -> str:
		status = "Active" if self.is_active else "Off"
		return f"<RulesetModifier(id={self.id}, type='{self.modifier_type}', field={self.calculation_field_id}, prio={self.priority})>"

class Ruleset(Base):
	"""
	Набор правил игры (Core Rules + Homebrew Overrides).
	Может наследоваться от родительского пресета.
	"""
	__tablename__ = "rulesets"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	owner_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True,
		comment="Владелец кастомного набора правил"
	)

	parent_ruleset_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("rulesets.id", ondelete="SET NULL"),
		nullable=True,
		index=True,
		comment="Наследование от базового пресета (например, Standard 5e)"
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	is_public: Mapped[bool] = mapped_column(Boolean(), default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# Флаг для быстрого отличия системных пресетов от пользовательских
	is_custom_ruleset: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)

	# --- Связи ---
	owner: Mapped["User | None"] = relationship("User", back_populates="rules_created", foreign_keys=[owner_id])
	parent_ruleset: Mapped["Ruleset | None"] = relationship(
		"Ruleset",
		remote_side=[id],
		backref="child_rulesets",
		post_update=True
	)

	characters: Mapped[list["Character"]] = relationship(
		"Character",
		back_populates="ruleset",
		passive_deletes=True
	)

	homebrew_entities: Mapped[list["HomebrewEntity"]] = relationship(
		"HomebrewEntity",
		back_populates="ruleset",
		foreign_keys="HomebrewEntity.ruleset_id",
		passive_deletes=True
	)

	# Вычислительный граф этого набора правил
	modifiers: Mapped[list[RulesetModifier]] = relationship(
		back_populates="ruleset",
		cascade="all, delete-orphan",
		order_by="RulesetModifier.priority",
		single_parent=True
	)

	def __repr__(self) -> str:
		mode = "Custom" if self.is_custom_ruleset else "Standard 5e"
		return f"<Ruleset(id={self.id}, name='{self.name}', mode='{mode}')>"