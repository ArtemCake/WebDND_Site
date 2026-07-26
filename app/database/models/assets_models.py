# app/database/models/assets_models.py

from Config.imports import (
	Integer, String, JSONB, DateTime, func, Boolean, ForeignKey,
	relationship, datetime, Mapped, mapped_column)
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

	metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # { width, height, duration_sec }

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