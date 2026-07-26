# app/database/models/bestiary_models.py

from Config.imports import (
	Integer, String, Text, Boolean, JSONB, ForeignKey, Float,
	relationship, datetime, DateTime, func, Mapped, mapped_column)
from app.database.database import Base


class Monster(Base):
	"""
	Справочник монстров (Бестиарий).
	Служит шаблоном для создания Токенов на карте во время боя.
	"""
	__tablename__ = "monsters"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	# Владение сущностью
	creator_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	campaign_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
	size: Mapped[str] = mapped_column(String(20), default="Medium") # Tiny, Small, Medium, Large...
	type_: Mapped[str] = mapped_column("type", String(50), nullable=False, index=True) # Humanoid, Undead, Dragon...

	alignment: Mapped[str | None] = mapped_column(String(20), nullable=True)
	armor_class: Mapped[int] = mapped_column(Integer, nullable=False)
	hit_points: Mapped[int] = mapped_column(Integer, nullable=False)
	speed: Mapped[int] = mapped_column(Integer, default=30)

	ability_scores: Mapped[dict] = mapped_column(JSONB, nullable=False) # {"str": 10, "dex": 14, ...}

	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	actions: Mapped[str | None] = mapped_column(Text, nullable=True) # Описание действий в JSON или Markdown

	challenge_rating: Mapped[float] = mapped_column(Float(), default=0.125) # CR 0, 1/8, 1/4... 30

	# Режим работы справочника
	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	homebrew_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	creator: Mapped["User | None"] = relationship()

	tokens: Mapped[list["Token"]] = relationship(
		back_populates="monster",
		primaryjoin="Monster.id == Token.monster_id",
		cascade="all, delete-orphan",
		lazy="selectin"
	)

	campaign: Mapped["Campaign | None"] = relationship(
		back_populates="monsters",
		foreign_keys=[campaign_id],
		lazy="selectin"
	)

	combat_encounters: Mapped[list["Encounter"]] = relationship(
		secondary="encounter_monsters",
		back_populates="monsters",
		lazy="selectin" # Оптимизация загрузки
	)

	def __repr__(self) -> str:
		return f"<Monster(id={self.id}, name='{self.name}', CR={self.challenge_rating})>"