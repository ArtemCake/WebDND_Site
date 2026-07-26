# app/database/models/campaign_models.py

from Config.imports import (
	Integer, String, Text, Boolean, DateTime, func, ForeignKey,
	relationship, datetime, Mapped, mapped_column)
from app.database.database import Base


class CampaignPlayerLink(Base):
	"""
	Участники кампании. Хранит права конкретного игрока внутри этого мира.
	"""
	__tablename__ = "campaign_players"

	campaign_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="CASCADE"),
		primary_key=True
	)
	user_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="CASCADE"),
		primary_key=True
	)

	role: Mapped[str] = mapped_column(String(20), default="PLAYER") # PLAYER, TRUSTED_PLAYER, READ_ONLY
	joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	campaign: Mapped["Campaign"] = relationship()
	user: Mapped["User"] = relationship(back_populates="joined_campaigns")

class Campaign(Base):
	"""
	Окампания (Мир/Сюжетная арка).
	Контейнер для всех карт, токенов, лора и игроков конкретной игры.
	"""
	__tablename__ = "campaigns"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	owner_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	system: Mapped[str] = mapped_column(String(50), default="D&D 5e") # D&D 5e, Pathfinder 2e и т.д.

	is_private: Mapped[bool] = mapped_column(Boolean(), default=True, index=True)
	invite_code: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True, index=True)

	visibility_mode: Mapped[str] = mapped_column(String(20), default="DEFAULT_FOG")
	# DEFAULT_FOG: скрыто всё, пока не открыл; REVEALED: открыто всё, Мастер закрывает туман войны вручную

	# Глобальные настройки домашних правил кампании
	ruleset_id: Mapped[int | None] = mapped_column(ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	dungeon_master: Mapped["User"] = relationship(back_populates="campaigns_owned")

	characters: Mapped[list["Character"]] = relationship(
		back_populates="campaign",
		passive_deletes=True
	)

	locations: Mapped[list["Location"]] = relationship(
		"Location",
		back_populates="campaign",
		cascade="all, delete-orphan",
		order_by="Location.order_index"
	)

	players: Mapped[list["User"]] = relationship(
		secondary="campaign_players",
		back_populates="joined_campaigns"
	)

	def __repr__(self) -> str:
		privacy = "Private" if self.is_private else "Public"
		return f"<Campaign(id={self.id}, name='{self.name}', DM={self.owner_id}, status={privacy})>"