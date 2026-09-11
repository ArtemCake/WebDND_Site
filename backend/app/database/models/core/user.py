# backend/app/models/core/user.py

"""Модели ядра системы: пользователи, аутентификация и социальные связи."""

from Config.imports import (Mapped, mapped_column, relationship, PG_UUID, datetime, uuid4, ForeignKey,
                            JSONB, func, CheckConstraint, String, Boolean, DateTime, Text,  UniqueConstraint)
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
	deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	# Связь с пользовательским контентом (Homebrew)
	created_homebrew_rules: Mapped[list["HomebrewRule"]] = relationship(
		"HomebrewRule", back_populates="owner", cascade="all, delete-orphan"
	)
	created_spells: Mapped[list["Spell"]] = relationship("Spell", back_populates="owner")
	created_races: Mapped[list["Race"]] = relationship("Race", back_populates="owner")
	created_languages: Mapped[list["Language"]] = relationship( "Language", back_populates="owner" )
	created_creatures: Mapped[list["Creature"]] = relationship( "Creature", back_populates="owner", cascade="all, delete-orphan")
	created_creature_sizes: Mapped[list["CreatureSize"]] = relationship( "CreatureSize", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_creature_types: Mapped[list["CreatureType"]] = relationship( "CreatureType", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_npcs: Mapped[list["NPC"]] = relationship( "NPC", back_populates="owner", cascade="all, delete-orphan")
	created_npc_types: Mapped[list["NPCTag"]] = relationship( "NPCTag", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_lore: Mapped[list["LoreEntry"]] = relationship("LoreEntry", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_classes: Mapped[list["CharacterClass"]] = relationship( "CharacterClass", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_subclasses: Mapped[list["Subclass"]] = relationship( "Subclass", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_backgrounds: Mapped[list["Background"]] = relationship("Background", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
	created_feats: Mapped[list["Feat"]] = relationship( "Feat", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_origins: Mapped[list["Origin"]] = relationship( "Origin", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_skills: Mapped[list["Skill"]] = relationship( "Skill", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	feats: Mapped[list["Feat"]] = relationship( "Feat", back_populates="owner", cascade="all, delete-orphan", lazy="selectin", overlaps="created_feats")
	skill_char_maps: Mapped[list["SkillCharacteristicMap"]] = relationship( "SkillCharacteristicMap", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_spell_levels: Mapped[list["SpellSlot"]] = relationship( "SpellSlot", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_magic_schools: Mapped[list["MagicSchool"]] = relationship( "MagicSchool", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_abilities: Mapped[list["Ability"]] = relationship( "Ability", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_effects: Mapped[list["Effect"]] = relationship( "Effect", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_damage_types: Mapped[list["DamageType"]] = relationship( "DamageType", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_equipment: Mapped[list["Equipment"]] = relationship( "Equipment", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )
	created_item_types: Mapped[list["ItemType"]] = relationship( "ItemType", back_populates="owner", cascade="all, delete-orphan", lazy="selectin" )

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