# backend/app/models/core/user.py

"""Модели ядра системы: пользователи, аутентификация и социальные связи."""

from Config.imports import (Mapped, mapped_column, relationship, PG_UUID, datetime, uuid4,
                            JSONB, func, CheckConstraint, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint)
from backend.app.database.database import Base


class User(Base):
	"""
	Основная таблица пользователей. Хранит учетные данные, настройки профиля и метаданные.
	"""
	__tablename__ = "users"
	__table_args__ = (
		# Защита от регистрации ников из пробелов или пустых строк
		CheckConstraint("nickname !~ '^\\s+$'", name="ck_user_nickname_not_blank"),
	)

	id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
	)
	email: Mapped[str] = mapped_column(
		String(255), unique=True, nullable=False, index=True
	)

	# Расширено до Text для безопасного хранения длинных хешей Argon2id без риска обрезки
	password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

	nickname: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

	avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
	profile_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)
	last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	# Для принудительного инвалида всех активных JWT/WebSocket сессий при смене пароля или блокировке
	active_session_token: Mapped[str | None] = mapped_column(String(512), index=True, nullable=True)

	# Отношения
	roles: Mapped[list["UserRole"]] = relationship(
		"UserRole", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
	)

	friends_from: Mapped[list["Friendship"]] = relationship(
		"Friendship",
		back_populates="user",
		foreign_keys="[Friendship.user_id]",
		cascade="all, delete-orphan",
		lazy="selectin"
	)

	friends_to: Mapped[list["Friendship"]] = relationship(
		"Friendship",
		back_populates="friend",
		foreign_keys="[Friendship.friend_user_id]",
		cascade="all, delete-orphan",
		lazy="selectin"
	)

	oauth_providers: Mapped[list["OAuthProvider"]] = relationship("OAuthProvider", back_populates="user", cascade="all, delete-orphan")
	mfa_devices: Mapped[list["MFADevice"]] = relationship("MFADevice", back_populates="user", cascade="all, delete-orphan")

	created_games: Mapped[list["Game"]] = relationship("Game", back_populates="master", cascade="all, delete-orphan")
	dice_rolls: Mapped[list["DiceRoll"]] = relationship("DiceRoll", back_populates="roller", cascade="all, delete-orphan")
	chat_messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender", cascade="all, delete-orphan")

	uploaded_assets: Mapped[list["UploadedAsset"]] = relationship("UploadedAsset", back_populates="uploader", cascade="all, delete-orphan")
	audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
	content_reports: Mapped[list["ContentReport"]] = relationship("ContentReport", back_populates="reporter", cascade="all, delete-orphan")

	# Связь с пользовательским контентом (Homebrew)
	created_homebrew_rules: Mapped[list["HomebrewRule"]] = relationship(
		"HomebrewRule", back_populates="owner", cascade="all, delete-orphan"
	)

	def __repr__(self) -> str:
		return f"<User(id='{self.id}', nickname='{self.nickname}', email='{self.email}')>"

class Friendship(Base):
	"""Таблица связей дружбы (Many-to-Many)."""
	__tablename__ = "friends"
	__table_args__ = (
		# Предотвращает добавление пользователя в друзья к самому себе на уровне БД
		CheckConstraint("user_id != friend_user_id", name="ck_friendship_no_self"),
	)

	user_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
	)
	friend_user_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
	)

	status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending") # pending, accepted, blocked
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	user: Mapped["User"] = relationship(
		"User", back_populates="friends_from", foreign_keys=[user_id]
	)
	friend: Mapped["User"] = relationship(
		"User", back_populates="friends_to", foreign_keys=[friend_user_id]
	)

class MFADevice(Base):
	"""Устройство двухфакторной аутентификации (TOTP)."""
	__tablename__ = "mfa_devices"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	user_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	type: Mapped[str] = mapped_column(String(20), nullable=False)
	secret: Mapped[str] = mapped_column(String(255), nullable=False)
	label: Mapped[str | None] = mapped_column(String(100), nullable=True)
	is_backup: Mapped[bool] = mapped_column(Boolean, default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	user: Mapped["User"] = relationship("User", back_populates="mfa_devices")

class OAuthProvider(Base):
	"""Привязанные социальные сети (ВК, Яндекс ID)."""
	__tablename__ = "user_providers"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	user_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	provider: Mapped[str] = mapped_column(String(50), nullable=False)
	external_id: Mapped[str] = mapped_column(String(255), nullable=False)
	access_token: Mapped[str] = mapped_column(Text, nullable=True)
	refresh_token: Mapped[str] = mapped_column(Text, nullable=True)
	expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	user: Mapped["User"] = relationship("User", back_populates="oauth_providers")

	__table_args__ = (UniqueConstraint("provider", "external_id", name="uq_provider_external_id"),)