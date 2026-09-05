# backend/app/models/gameplay/lobby.py

"""Модели игрового процесса: игры, приглашения и участники."""

from Config.imports import (Mapped, mapped_column, relationship, JSONB, text, datetime,
                            PG_UUID, String, Text, Integer, Boolean, DateTime, ForeignKey,
							ARRAY, datetime, uuid4)
from backend.app.database.database import Base


# --- ИГРЫ ---
class Game(Base):
	"""
	Настольная игра (сессия или кампания).
	Реализует требование ТЗ о создании игр мастером с разными статусами приватности.
	"""
	__tablename__ = "games"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	master_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	system_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("game_systems.id", ondelete="CASCADE"), nullable=False, index=True
	)

	title: Mapped[str] = mapped_column(String(255), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft") # 'draft', 'active', 'archived'

	privacy_level: Mapped[str] = mapped_column(String(20), nullable=False, server_default="private")
	# 'public' - поиск открыт, 'friends_only', 'invite_only', 'private'

	voice_chat_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"provider": "discord", "channel_id": "..."}

	is_homebrew_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	master: Mapped["User"] = relationship("User", back_populates="created_games")
	system: Mapped["GameSystem"] = relationship("GameSystem")
	party: Mapped[list["Party"]] = relationship("Party", back_populates="game", cascade="all, delete-orphan")
	invites: Mapped[list["Invite"]] = relationship("Invite", back_populates="game", cascade="all, delete-orphan")
	sessions: Mapped[list["Session"]] = relationship("Session", back_populates="game", cascade="all, delete-orphan")
	campaign_maps: Mapped[list["CampaignMap"]] = relationship("CampaignMap", back_populates="game", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Game(id='{self.id}', title='{self.title}', status='{self.status}')>"

# --- УЧАСТНИКИ ИГРЫ ---
class Party(Base):
	"""
	Промежуточная таблица связи пользователей и игр.
	Реализует требование ТЗ о поиске игр, приглашениях и ролях внутри кампании.
	"""
	__tablename__ = "party"

	game_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
	)
	user_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
	)

	joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

	# Роль в конкретной игре (может отличаться от глобальной роли пользователя)
	role_in_game: Mapped[str] = mapped_column(String(20), nullable=False, server_default="player")
	# 'player', 'assistant_dm' (со-мастер), 'banned'

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	# False - игрок исключен из текущей сессии, но история сохранится

	notification_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"mentions": true, "session_start": true}

	game: Mapped["Game"] = relationship("Game", back_populates="party")
	user: Mapped["User"] = relationship("User")
	character_sheets: Mapped[list["CharacterSheet"]] = relationship(
		"CharacterSheet", back_populates="game_link", cascade="all, delete-orphan"
	)
	dice_rolls: Mapped[list["DiceRoll"]] = relationship(
		"DiceRoll", back_populates="roller_session", cascade="all, delete-orphan"
	)

	def __repr__(self) -> str:
		return f"<Party(game_id='{self.game_id}', user_id='{self.user_id}', role='{self.role_in_game}')>"

# --- ПРИГЛАШЕНИЯ ---
class Invite(Base):
	"""
	Приглашение в игру.
	Реализует требование ТЗ о 10-минутном сроке жизни приглашения.
	"""
	__tablename__ = "invites"

	token: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False) # Случайная строка

	game_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
	)

	creator_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	claimed_by: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

	uses_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1") # Обычно одноразовое
	uses_current: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

	message: Mapped[str | None] = mapped_column(Text, nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	game: Mapped["Game"] = relationship("Game", back_populates="invites")
	creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
	claimer: Mapped["User"] = relationship("User", foreign_keys=[claimed_by])

	def __repr__(self) -> str:
		return f"<Invite(token='{self.token[:8]}...', game_id='{self.game_id}', expired={self.is_expired})>"

	@property
	def is_expired(self) -> bool:
		from datetime import datetime, timezone
		now = datetime.now(timezone.utc)
		return self.expires_at <= now or self.uses_current >= self.uses_limit

	def consume(self):
		"""Увеличивает счетчик использований."""
		if not self.is_expired:
			self.uses_current += 1

# --- ИГРОВЫЕ СЕССИИ ---
class Session(Base):
	"""
	Конкретная игровая сессия внутри кампании.
	Реализует требование ТЗ о хранении истории действий и логов игры.
	"""
	__tablename__ = "sessions"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	game_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
	)

	title: Mapped[str | None] = mapped_column(String(255), nullable=True) # Название встречи (например, 'Засада в таверне')
	summary_log: Mapped[str | None] = mapped_column(Text, nullable=True) # Краткий пересказ событий мастером

	start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	game: Mapped["Game"] = relationship("Game", back_populates="sessions")
	initiative: Mapped["InitiativeTracker"] = relationship(
		"InitiativeTracker", uselist=False, back_populates="session", cascade="all, delete-orphan"
	)
	dice_rolls: Mapped[list["DiceRoll"]] = relationship(
		"DiceRoll", back_populates="session", cascade="all, delete-orphan"
	)
	chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="session", cascade="all, delete-orphan")
	maps: Mapped[list["CampaignMap"]] = relationship(
		"CampaignMap", back_populates="session", cascade="all, delete-orphan"
	)
	tokens: Mapped[list["Token"]] = relationship("Token", back_populates="session", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Session(id='{self.id}', game_id='{self.game_id}', active={self.is_active})>"

# --- ОЧЕРЕДЬ ХОДОВ ---
class InitiativeTracker(Base):
	"""
	Состояние очереди инициативы для конкретной сессии.
	Реализует требование ТЗ о хранении истории действий и текущего раунда.
	"""
	__tablename__ = "initiative_tracker"

	session_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
	)

	turn_order_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
	# Структура: [
	#   {"entity_type": "npc", "entity_id": "uuid...", "name": "Гоблин", "initiative": 15, "hp_current": 7},
	#   {"entity_type": "pc", "character_sheet_id": "uuid...", "name": "Файтер", "initiative": 12, "hp_current": 25}
	# ]

	current_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Индекс в массиве turn_order
	round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	session: Mapped["Session"] = relationship("Session", back_populates="initiative")

	def __repr__(self) -> str:
		return f"<InitiativeTracker(session_id='{self.session_id}', round={self.round_number})>"

# --- БРОСКИ КУБИКОВ ---
class DiceRoll(Base):
	"""
	Лог бросков кубиков.
	Реализует требование ТЗ о поддержке помех, преимуществ и скрытых бросков мастера.
	"""
	__tablename__ = "dice_rolls"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	session_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
	)

	roller_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	npc_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="SET NULL"), nullable=True, index=True
	)

	# Формула в человекочитаемом виде
	formula: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. '1d20+5', '8d6 fire'

	result_total: Mapped[int] = mapped_column(Integer, nullable=False)
	individual_results: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False) # [3, 7, 1]

	advantage: Mapped[str | None] = mapped_column(String(10), nullable=True) # 'advantage', 'disadvantage', null
	is_gm_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Требование ТЗ: бросок «в закрытую»

	context_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # 'attack', 'save', 'damage', 'skill'
	context_target_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True) # ID персонажа или НПС, против которого бросок

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

	session: Mapped["Session"] = relationship("Session", back_populates="dice_rolls")
	roller: Mapped["User"] = relationship("User", back_populates="dice_rolls")
	npc: Mapped["NPC"] = relationship("NPC", back_populates="dice_rolls")

	def __repr__(self) -> str:
		return f"<DiceRoll(id='{self.id}', formula='{self.formula}', total={self.result_total})>"