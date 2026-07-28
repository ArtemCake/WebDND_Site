# app/database/models/campaign_models.py

from Config.imports import (
	Integer, String, Text, Boolean, DateTime, func, ForeignKey,
	relationship, datetime, Mapped, mapped_column, JSONB,UUID, remote)
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
	user: Mapped["User"] = relationship(back_populates="link_user")

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
		back_populates="joined_campaigns",
		viewonly=True,
		overlaps="link_user"
	)

	lore_articles: Mapped[list["LoreArticle"]] = relationship(
		back_populates="campaign",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	monsters: Mapped[list["Monster"]] = relationship(
		back_populates="campaign",
		foreign_keys="Monster.campaign_id",
		cascade="all, delete-orphan",
		lazy="selectin"
	)

	invitations: Mapped[list["Invitation"]] = relationship(
		back_populates="campaign"
	)

	ruleset: Mapped["Ruleset | None"] = relationship(
		"Ruleset",
		back_populates="campaign",
		foreign_keys=[ruleset_id],
		uselist=False,
		overlaps="characters, dungeon_master"
	)

	def __repr__(self) -> str:
		privacy = "Private" if self.is_private else "Public"
		return f"<Campaign(id={self.id}, name='{self.name}', DM={self.owner_id}, status={privacy})>"

class Session(Base):
	"""
	Хранит данные серверной сессии пользователя.
	Используется реже, чем JWT, если нужно хранить тяжелые данные на сервере.
	"""
	__tablename__ = "sessions"

	id: Mapped[str] = mapped_column(
		String(128), # Обычно здесь хранится ID куки или JTI токена
		primary_key=True,
		default=lambda: str(UUID.uuid4())
	)

	user_id: Mapped[int | None] = mapped_column(
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=True,
		index=True
	)

	data: Mapped[dict | None] = mapped_column(JSONB) # Сериализованные данные сессии

	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	user: Mapped["User | None"] = relationship(back_populates="sessions")

class Invitation(Base):
	"""
	Приглашение пользователя в кампанию по ссылке или ID.
	"""
	__tablename__ = "invitations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	campaign_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	inviter_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	) # Кто пригласил

	invite_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

	status: Mapped[str] = mapped_column(String(20), default="PENDING") # PENDING, ACCEPTED, REVOKED, EXPIRED

	expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	campaign: Mapped["Campaign"] = relationship(back_populates="invitations")
	inviter: Mapped["User | None"] = relationship()

class Lobby(Base):
	__tablename__ = "lobbies"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	owner_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
	)
	name: Mapped[str] = mapped_column(String(100), nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

	# Обратная связь к пользователю
	owner: Mapped["User"] = relationship(back_populates="lobbies_owned")

