# backend/app/models/systems/system.py

"""Служебные модели: логи, кэш и системные события."""

from Config.imports import (String, Text, Integer, Boolean, DateTime, ForeignKey,
						Mapped, mapped_column, relationship, JSONB, text, PG_UUID, datetime, uuid4)
from backend.app.database.database import Base


# --- ЛОГИ АУДИТА ---
class AuditLog(Base):
	"""
	Журнал критических действий пользователей.
	Реализует требование ТЗ о слежке за изменениями каноничного контента (№58)
	и соответствует стандартам безопасности 2026 года.
	"""
	__tablename__ = "audit_logs"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	user_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True) # Поддержка IPv6
	action_type: Mapped[str] = mapped_column(String(50), nullable=False)
	# 'login', 'logout', 'homebrew_edit', 'admin_delete_user'
	table_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
	record_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
	old_value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	new_value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
	severity_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False) # 1-Info, 3-Warn, 5-Critical
	is_read_by_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	user: Mapped["User"] = relationship("User", back_populates="audit_logs")

	def __repr__(self) -> str:
		return f"<AuditLog(id='{self.id}', action='{self.action_type}', level={self.severity_level})>"

# --- СИСТЕМНЫЕ СОБЫТИЯ ---
class SystemEvent(Base):
	"""
	Технические логи бэкенда.
	Реализует требование ТЗ о слежке за состоянием WebSocket и брокера Redis (№59).
	Используется для отладки real-time механик (туман войны, кубики).
	"""
	__tablename__ = "system_events"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	event_type: Mapped[str] = mapped_column(String(50), nullable=False)
	# 'socket_connect', 'redis_pubsub_error', 'mfa_challenge_failed'
	severity_level: Mapped[int] = mapped_column(Integer, default=2, nullable=False) # 1-Debug, 3-Error, 5-Fatal
	message: Mapped[str] = mapped_column(Text, nullable=False)
	metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"room_id": "game_abc", "user_socket": "sid_xxx", "retry_attempt": 2}
	stacktrace: Mapped[str | None] = mapped_column(Text, nullable=True)
	acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

	def __repr__(self) -> str:
		return f"<SystemEvent(id='{self.id}', type='{self.event_type}', level={self.severity_level})>"

# --- КЭШ АКТИВНЫХ СЕССИЙ ---
class ActiveSessionCache(Base):
	"""
	Таблица-заглушка или зеркало состояния Redis.
	Реализует требование ТЗ о быстром доступе Socket.ID -> User_ID (№60) и поддержке высокой нагрузки.

	ПРИМЕЧАНИЕ: В production-среде 2026 года эта таблица фактически не используется,
	так как данные живут в оперативной памяти Redis/Platform V Pangolin.
	Однако её наличие необходимо для миграций и работы Alembic при локальной разработке без Redis.
	"""
	__tablename__ = "active_sessions_cache"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	user_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
	socket_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True) # e.g. 'socket_id_abc123'
	connection_info_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	# {"ip": "192.168.1.1", "latency_ms": 12, "protocol": "websocket"}
	last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	is_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	current_game_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL"), nullable=True, index=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	user: Mapped["User"] = relationship("User")
	game: Mapped["Game"] = relationship("Game")

	def __repr__(self) -> str:
		return f"<ActiveSessionCache(user='{self.user_id}', socket='{self.socket_id}')>"

# --- ЖАЛОБЫ НА КОНТЕНТ ---
class ContentReport(Base):
	"""
	Жалоба пользователя на Homebrew-контент.
	Реализует требование ТЗ о модерации пользовательского контента (№61) и безопасности сообщества.
	"""
	__tablename__ = "content_reports"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	reporter_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	target_table: Mapped[str] = mapped_column(String(50), nullable=False) # 'spells', 'feats', 'races'
	target_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
	reason: Mapped[str] = mapped_column(String(100), nullable=False)
	# enum: ['copyright_violation', 'nsfw_content', 'broken_mechanic', 'harassment']
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	moderator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
	status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="new")
	# enum: ['new', 'under_review', 'approved', 'rejected', 'actioned']
	severity_score: Mapped[int] = mapped_column(Integer, default=1, nullable=False) # 1-10, рассчитывается ИИ-модератором
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	reporter: Mapped["User"] = relationship("User", back_populates="content_reports")
	target_owner: Mapped["User"] = relationship("User", foreign_keys=[target_id]) # Владелец контента

	def __repr__(self) -> str:
		return f"<ContentReport(id='{self.id}', table='{self.target_table}', status='{self.status}')>"