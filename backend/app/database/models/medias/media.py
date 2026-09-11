# backend/app/models/medias/media.py

"""Модели медиа-контента и ассетов."""

from Config.imports import (String, Text, Integer, Boolean, DateTime, ForeignKey,
						Mapped, mapped_column, relationship, text, PG_UUID, JSONB,datetime,
						uuid4)
from backend.app.database.database import Base


# --- ЗАГРУЖЕННЫЕ АССЕТЫ ---
class UploadedAsset(Base):
	"""
	Загруженный пользователем файл (карта, токен, изображение предмета).
	Реализует требование ТЗ о хранении истории загрузок (№56) и генерации через ИИ (№57).
	"""
	__tablename__ = "uploaded_assets"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	uploader_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	# Ссылка на конкретный предмет или карту, где используется этот ассет
	equipment_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True, index=True)
	campaign_map_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaign_maps.id", ondelete="SET NULL"), nullable=True, index=True)
	storage_path: Mapped[str] = mapped_column(String(1000), nullable=False) # Путь в S3 /volume Amvera
	original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
	mime_type: Mapped[str] = mapped_column(String(100), nullable=False) # 'image/png', 'application/pdf'
	file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
	width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
	height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
	dpi: Mapped[int | None] = mapped_column(Integer, nullable=True)
	is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Доступ по прямой ссылке
	usage_rights: Mapped[str] = mapped_column(String(50), nullable=False, server_default="private")
	# 'all_users', 'game_only', 'owner_only' (Требование ТЗ про разрешение использования)
	ai_prompt: Mapped[str | None] = mapped_column(Text, nullable=True) # Промпт, если сгенерировано нейросетью
	generation_job_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_generation_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	uploader: Mapped["User"] = relationship("User", back_populates="uploaded_assets")
	equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="assets")
	map: Mapped["CampaignMap"] = relationship("CampaignMap")
	job: Mapped["AIGenerationJob"] = relationship("AIGenerationJob")

	def __repr__(self) -> str:
		return f"<UploadedAsset(id='{self.id}', path='{self.storage_path}')>"

# --- ЗАДАЧИ ГЕНЕРАЦИИ ИИ ---
class AIGenerationJob(Base):
	"""
	Задача на генерацию изображения или 3D-модели нейросетью.
	Реализует требование ТЗ об использовании актуальных технических решений 2026 года (№41, 43-45)
	и интеграции с AI-сервисами.
	"""
	__tablename__ = "ai_generation_jobs"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	owner_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	target_asset_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("uploaded_assets.id", ondelete="SET NULL"), nullable=True, index=True)
	model_used: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'Kandinsky-5.0', 'StableDiffusion-XL-Turbo'
	prompt: Mapped[str] = mapped_column(Text, nullable=False)
	negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
	status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
	# enum: ['pending', 'processing', 'completed', 'failed']
	priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Для брокера задач Redis/Celery
	cost_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Внутренняя валюта за GPU-время
	progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	result_metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"seed": 42, "steps": 20, "sampler": "euler_a"}
	error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	owner: Mapped["User"] = relationship("User", back_populates="created_ai_jobs")
	asset: Mapped["UploadedAsset"] = relationship("UploadedAsset", back_populates="job")

	def __repr__(self) -> str:
		return f"<AIGenerationJob(id='{self.id}', status='{self.status}', model='{self.model_used}')>"