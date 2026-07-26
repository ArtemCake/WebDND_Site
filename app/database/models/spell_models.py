# app/database/models/spell_models.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey,
	relationship, datetime, DateTime, func, Mapped, mapped_column)
from app.database.database import Base


# Связующая таблица Класс <-> Заклинание (какие заклы доступны классу по умолчанию)
class ClassSpellLink(Base):
	__tablename__ = "class_spells"

	class_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("classes.id", ondelete="CASCADE"),
		primary_key=True
	)
	spell_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("spells.id", ondelete="CASCADE"),
		primary_key=True
	)

	# На каком уровне класса это заклинание становится доступно (если применимо)
	available_at_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

	base_class: Mapped["Class"] = relationship(back_populates="spells")
	spell: Mapped["Spell"] = relationship()

class Spell(Base):
	"""
	Базовый справочник заклинаний (SRD или Homebrew).
	"""
	__tablename__ = "spells"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

	level: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 0 для заговоров (cantrips)
	school: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # Evocation, Necromancy и т.д.

	casting_time: Mapped[str] = mapped_column(String(100), nullable=False)
	range_: Mapped[str] = mapped_column("range", String(100), nullable=False)
	components: Mapped[str] = mapped_column(Text, nullable=False) # V, S, M (xxx gp)
	duration: Mapped[str] = mapped_column(String(100), nullable=False)

	description: Mapped[str] = mapped_column(Text, nullable=False)
	higher_levels: Mapped[str | None] = mapped_column(Text, nullable=True)

	is_ritual: Mapped[bool] = mapped_column(Boolean(), default=False)
	concentration: Mapped[bool] = mapped_column(Boolean(), default=False)

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	classes: Mapped[list["Class"]] = relationship(
		secondary="class_spells",
		back_populates="spells"
	)

	character_spells: Mapped[list["CharacterSpell"]] = relationship(back_populates="spell")

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Spell(id={self.id}, name='{self.name}', LvL={self.level}, status={status})>"
