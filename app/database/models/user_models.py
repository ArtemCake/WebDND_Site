# app/database/models/user_models.py

from Config.imports import (
	DateTime, func, SQLEnum, Enum, Index,
	Integer, String, Text, Boolean, ForeignKey,
	relationship, datetime, Mapped, mapped_column)
from app.database.database import Base
from app.enums.log_enums import LogLevelEnum, LogAction
from app.enums.user_enums import Role_enums


class UserLog(Base):
	"""
	Журнал действий конкретного пользователя.
	Привязан к пользователю через user_id.
	"""
	__tablename__ = "user_logs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)
	action: Mapped[LogAction] = mapped_column(SQLEnum(LogAction, native_enum=True, create_constraint=False), nullable=False, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	log_level: Mapped[LogLevelEnum] = mapped_column(
		SQLEnum(LogLevelEnum, native_enum=True, create_constraint=False),
		nullable=False,
		default=LogLevelEnum.INFO,
		index=True
	)
	timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# Связь обратно к пользователю
	user: Mapped["User"] = relationship(back_populates="logs")

	def __repr__(self) -> str:
		return f"<UserLog(id={self.id}, user_id={self.user_id}, action={self.action.value})>"

class AppLog(Base):
	"""
	Глобальный журнал приложения.
	Не привязан жестко к ID юзера строкой FK, чтобы логи сохранялись даже при удалении пользователя.
	"""
	__tablename__ = "app_logs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	username: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
	action: Mapped[LogAction] = mapped_column(SQLEnum(LogAction, native_enum=True, create_constraint=False), nullable=False, index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
	log_level: Mapped[LogLevelEnum] = mapped_column(
		SQLEnum(LogLevelEnum, native_enum=True, create_constraint=False),
		nullable=False,
		default=LogLevelEnum.INFO,
		index=True
	)

	def __repr__(self) -> str:
		actor = self.username or "System"
		return f"<AppLog(id={self.id}, user='{actor}', action={self.action.value})>"

class User(Base):
	"""
	Основная модель пользователя системы.
	"""
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

	role: Mapped[Role_enums] = mapped_column(Enum(Role_enums, native_enum=True, create_constraint=False),
	                                         default=Role_enums.PLAYER,
	                                         nullable=False)

	gdpr_consent: Mapped[bool] = mapped_column(Boolean(), default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- НОВЫЕ ПОЛЯ ДЛЯ УПРАВЛЕНИЯ ТАБЛИЦАМИ ---
	# Позволяет Мастеру отключать конкретные модули контента для своих миров
	use_custom_races: Mapped[bool] = mapped_column(Boolean(), default=True)
	use_custom_classes: Mapped[bool] = mapped_column(Boolean(), default=True)
	use_custom_spells: Mapped[bool] = mapped_column(Boolean(), default=True)
	use_custom_items: Mapped[bool] = mapped_column(Boolean(), default=True)

	# --- СВЯЗИ ---
	characters: Mapped[list["Character"]] = relationship(
		"Character",
		back_populates="user",
		foreign_keys="Character.user_id",
		passive_deletes=True,
		cascade="all, delete-orphan"
	)

	logs: Mapped[list[UserLog]] = relationship(
		"UserLog",
		back_populates="user",
		order_by=UserLog.timestamp.desc(),
		passive_deletes=True,
		cascade="all, delete-orphan"
	)

	rules_created: Mapped[list["Ruleset"]] = relationship(
		"Ruleset",
		back_populates="owner",
		foreign_keys="Ruleset.owner_id",
		cascade="all, delete-orphan"
	)

	homebrew_entities: Mapped[list["HomebrewEntity"]] = relationship(
		"HomebrewEntity",
		back_populates="creator",
		foreign_keys="HomebrewEntity.creator_id",
		passive_deletes=True,
		cascade="all, delete-orphan"
	)

	lobbies_owned: Mapped[list["Lobby"]] = relationship(
		"Lobby",
		back_populates="owner",
		cascade="all, delete-orphan"
	)

	campaigns_owned: Mapped[list["Campaign"]] = relationship(
		"Campaign",
		back_populates="dungeon_master",
		cascade="all, delete-orphan"
	)

	table_args = (
		Index('ix_users_username_active', 'username', postgresql_where=(is_active == True)),
	)

	def __repr__(self) -> str:
		status = "Active" if self.is_active else "Banned"
		return f"<User(id={self.id}, username='{self.username}', role={self.role.value}, status={status})>"
	"""
	Основная модель пользователя системы.
	"""
	__tablename__ = "users"
	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
	role: Mapped[Role_enums] = mapped_column(Enum(Role_enums, native_enum=True, create_constraint=False),
	                                         default=Role_enums.PLAYER,
	                                         nullable=False)
	gdpr_consent: Mapped[bool] = mapped_column(Boolean(), default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	# Персонажи этого пользователя
	characters: Mapped[list["Character"]] = relationship(
		"Character",
		back_populates="user",
		foreign_keys="Character.user_id",
		passive_deletes=True,
		cascade="all, delete-orphan"
	)
	# Логи действий именно этого пользователя
	logs: Mapped[list[UserLog]] = relationship(
		"UserLog",
		back_populates="user",
		order_by=UserLog.timestamp.desc(),
		passive_deletes=True,
		cascade="all, delete-orphan"
	)
	# Права доступа / кастомные наборы правил, созданные этим пользователем
	rules_created: Mapped[list["Ruleset"]] = relationship(
		"Ruleset",
		back_populates="owner",
		foreign_keys="Ruleset.owner_id",
		cascade="all, delete-orphan"
	)
	# Кастомный контент (хоумбрю), созданный пользователем
	homebrew_entities: Mapped[list["HomebrewEntity"]] = relationship(
		"HomebrewEntity",
		back_populates="creator",
		foreign_keys="HomebrewEntity.creator_id",
		passive_deletes=True,
		cascade="all, delete-orphan"
	)
	sessions: Mapped[list["Session"]] = relationship(
		"Session",
		back_populates="user",
		passive_deletes=True,
		cascade="all, delete-orphan"
	)
	# Приглашения, созданные этим пользователем
	sent_invitations: Mapped[list["Invitation"]] = relationship(
		"Invitation",
		back_populates="inviter",
		foreign_keys="Invitation.inviter_id",
		cascade="all, delete-orphan"
	)
	joined_campaigns: Mapped[list["Campaign"]] = relationship(
		   secondary="campaign_players",
		     back_populates="players"
		 )
	homebrew_assets: Mapped[list["AssetLibraryEntry"]] = relationship(
		     "AssetLibraryEntry",
		     back_populates="owner",
		     foreign_keys="AssetLibraryEntry.owner_id",
		     passive_deletes=True,
		     cascade="all, delete-orphan"
		 )

	encounters_created: Mapped[list["Encounter"]] = relationship(
	     "Encounter",
	     back_populates="dungeon_master",
	     foreign_keys="Encounter.dungeon_master_id",
	     cascade="all, delete-orphan"
	)

	# Индекс для быстрого поиска активных пользователей по нику
	__table_args__ = (
		Index('ix_users_username_active', 'username', postgresql_where=(is_active == True)),
	)

	def __repr__(self) -> str:
		status = "Active" if self.is_active else "Banned"
		return f"<User(id={self.id}, username='{self.username}', role={self.role.value}, status={status})>"