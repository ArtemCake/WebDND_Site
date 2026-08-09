# app/database/models/assets_models.py

from Config.imports import (
	Integer, String, JSONB, DateTime, func, Boolean, ForeignKey,
	relationship, datetime, Mapped, mapped_column, Text)
from app.database.database import Base


class AssetLibraryEntry(Base):
	"""
	Загруженный файл пользователя (токен НПС, карта, аудиоэффект).
	Хранит метаинформацию. Сами бинарные данные лежат во внешнем хранилище (S3/minio/VK Object Storage).
	"""
	__tablename__ = "asset_library_entries"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	owner_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	campaign_id: Mapped[int | None] = mapped_column(
		ForeignKey("campaigns.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	filename: Mapped[str] = mapped_column(String(255), nullable=False)
	file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
	mime_type: Mapped[str] = mapped_column(String(100), nullable=False) # image/png, audio/mp3

	storage_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True) # Ключ объекта в S3
	thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True) # Ссылка на превью

	asset_category: Mapped[str] = mapped_column(String(50), default="GENERAL") # TOKEN, MAP_BACKGROUND, AUDIO, DM_SCREEN

	is_public_gallery: Mapped[bool] = mapped_column(Boolean(), default=False) # Разрешить другим мастерам использовать этот асссет?

	custom_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # { width, height, duration_sec }

	uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	owner: Mapped["User"] = relationship(back_populates="homebrew_assets")
	campaign: Mapped["Campaign | None"] = relationship()

	used_in_tokens: Mapped[list["Token"]] = relationship(
		"Token",
		foreign_keys="Token.custom_asset_id",
		back_populates="custom_asset"
	)

	def __repr__(self) -> str:
		scope = "Global" if self.is_public_gallery else "Private"
		return f"<Asset(id={self.id}, file='{self.filename}', cat={self.asset_category}, scope={scope})>"

class Ruleset(Base):
	"""
	Набор правил (Ruleset) для конкретной кампании.
	Позволяет переопределять механики SRD без изменения кода.
	"""
	__tablename__ = "rulesets"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

	campaign_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	owner_id: Mapped[int | None] = mapped_column(  # <-- ДОБАВИТЬ
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False) # Например: "My Homebrew D&D 5e"
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Переопределение базовых формул (примеры)
	death_save_success_dc: Mapped[int] = mapped_column(Integer, default=10)
	short_rest_dice_count: Mapped[int] = mapped_column(Integer, default=0) # Сколько кубиков восстанавливается

	# Кастомные бонусы к спасброскам или скиллам на уровне всей кампании
	global_modifiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true", index=True)
	is_homebrew: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	campaign: Mapped["Campaign"] = relationship(
		back_populates="ruleset",
		foreign_keys=[campaign_id],
		uselist=False
	)

	owner: Mapped["User | None"] = relationship(
		back_populates="rules_created",
		foreign_keys=[owner_id], # <--- Явно указываем локальный FK
		overlaps="joined_campaigns, campaigns_owned" # Указываем другие связи User, использующие users.id
	)

	def __repr__(self) -> str:
		status = "Homebrew" if self.is_homebrew else "SRD"
		return f"<Ruleset(id={self.id}, name='{self.name}', status={status})>"

class HomebrewEntity(Base):
	"""
	Универсальная сущность для любого домашнего контента
	(Расы, Заклинания, Монстры, Магические предметы).
	"""
	__tablename__ = "homebrew_entities"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)

	owner_id: Mapped[int | None] = mapped_column(
		Integer,
		ForeignKey("users.id", ondelete="SET NULL"),
		nullable=True,
		index=True
	)

	# Полиморфная привязка к типу сущности
	entity_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'spell', 'race', 'item'

	name: Mapped[str] = mapped_column(String(150), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)

	raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # Весь объект заклинания/предмета целиком

	is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


	owner: Mapped["User | None"] = relationship(back_populates="homebrew_entities")
