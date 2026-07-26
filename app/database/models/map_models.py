# app/database/models/map_models.py

from Config.imports import (
	Integer, String, DateTime, func, Float, Boolean, JSONB, ForeignKey,
	relationship, datetime, Mapped, mapped_column)
from app.database.database import Base


class Location(Base):
	"""Сцена или Карта. Виртуальный стол."""
	__tablename__ = "locations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	background_url: Mapped[str] = mapped_column(String(500), nullable=False)

	grid_size: Mapped[float] = mapped_column(Float(), default=5.0)
	width_px: Mapped[int] = mapped_column(Integer, nullable=False)
	height_px: Mapped[int] = mapped_column(Integer, nullable=False)

	fog_of_war_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	order_index: Mapped[int] = mapped_column(Integer, default=0)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	campaign: Mapped["Campaign"] = relationship(back_populates="locations")
	tokens: Mapped[list["Token"]] = relationship(
		"Token",
		back_populates="location",
		cascade="all, delete-orphan",
		passive_deletes=True
	)
	walls: Mapped[list["Wall"]] = relationship(
	     back_populates="location",
	     cascade="all, delete-orphan",
	     passive_deletes=True
	)

	lights: Mapped[list["LightSource"]] = relationship(
	     back_populates="location",
	     cascade="all, delete-orphan"
	)

	def __repr__(self) -> str:
		return f"<Location(id={self.id}, name='{self.name}', bg={self.background_url.split('/')[-1]})>"

class Token(Base):
	"""
	Фигурка на карте (Токен).
	"""
	__tablename__ = "tokens"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	location_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
	)

	character_id: Mapped[int | None] = mapped_column(
		ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True
	)

	# ДЛЯ ТОКЕНОВ МОНСТРОВ — добавь эту колонку
	monster_id: Mapped[int | None] = mapped_column(
		ForeignKey("monsters.id", ondelete="SET NULL"), nullable=True, index=True
	)

	x_coord: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
	y_coord: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
	z_index: Mapped[int] = mapped_column(Integer, default=0)

	scale: Mapped[float] = mapped_column(Float(), default=1.0)
	rotation_deg: Mapped[float] = mapped_column(Float(), default=0.0)

	vision_radius: Mapped[float | None] = mapped_column(Float(), nullable=True)
	emits_light: Mapped[bool] = mapped_column(Boolean(), default=False)

	is_locked: Mapped[bool] = mapped_column(Boolean(), default=False)
	is_visible_to_players: Mapped[bool] = mapped_column(Boolean(), default=True)

	custom_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

	custom_asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset_library_entries.id", ondelete="SET NULL"), nullable=True, index=True)

	# --- СВЯЗИ ---
	location: Mapped["Location"] = relationship(back_populates="tokens")
	character: Mapped["Character | None"] = relationship()
	custom_asset: Mapped["AssetLibraryEntry | None"] = relationship(back_populates="used_in_tokens")
	active_effects: Mapped[list["ActiveEffect"]] = relationship(
		back_populates="token",
		cascade="all, delete-orphan"
	)

		# Связь на монстра (обратная к Monster.tokens)
	monster: Mapped["Monster | None"] = relationship(
		back_populates="tokens",
		foreign_keys=[monster_id],
		lazy="selectin"
	)

	def __repr__(self) -> str:
		char_name = self.character.name if self.character else "Prop"
		return f"<Token(id={self.id}, entity='{char_name}', pos=[{self.x_coord:.1f}, {self.y_coord:.1f}])>"

# --- МОДЕЛЬ СТЕНЫ ---
class Wall(Base):
	"""
	Стена или препятствие на карте. Используется для:
	1. Физической блокировки движения Token-ов.
	2. Расчета Line of Sight (Тумана войны).
	"""
	__tablename__ = "walls"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	location_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("locations.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	# Координаты отрезка стены
	x1: Mapped[float] = mapped_column(Float(), nullable=False)
	y1: Mapped[float] = mapped_column(Float(), nullable=False)
	x2: Mapped[float] = mapped_column(Float(), nullable=False)
	y2: Mapped[float] = mapped_column(Float(), nullable=False)

	# Толщина стены в футах (для расчетов проходимости)
	thickness_feet: Mapped[float] = mapped_column(Float(), default=0.5)

	blocks_sight: Mapped[bool] = mapped_column(Boolean(), default=True, index=True)
	blocks_movement: Mapped[bool] = mapped_column(Boolean(), default=True, index=True)

	# Для дверей: прозрачность и состояние
	is_door: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
	is_open: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false", index=True)
	door_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # wooden, iron, secret

	location: Mapped["Location"] = relationship(back_populates="walls")

	def __repr__(self) -> str:
		return f"<Wall(id={self.id}, loc={self.location_id}, p=[{self.x1},{self.y1}] -> [{self.x2},{self.y2}])>"

# --- МОДЕЛЬ ИСТОЧНИКА СВЕТА ---
class LightSource(Base):
	"""
	Источник света. Может быть закреплен за Токеном или висеть в точке пространства.
	"""
	__tablename__ = "light_sources"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	location_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("locations.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	# Привязка к объекту (опционально)
	token_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("tokens.id", ondelete="SET NULL"), nullable=True, index=True
	)

	# Координаты центра источника (если не привязан к токену)
	x_coord: Mapped[float | None] = mapped_column(Float(), nullable=True)
	y_coord: Mapped[float | None] = mapped_column(Float(), nullable=True)

	color: Mapped[str] = mapped_column(String(7), default="#ffffff") # Hex цвет (#ffd700 - золото)
	brightness: Mapped[float] = mapped_column(Float(), default=1.0) # Множитель яркости

	vision_radius: Mapped[float] = mapped_column(Float(), nullable=False) # Радиус освещения
	bright_radius: Mapped[float | None] = mapped_column(Float(), nullable=True) # Радиус ЯРКОГО света (dim light далее)

	dimming_exponent: Mapped[float] = mapped_column(Float(), default=2.0) # Как быстро падает освещенность

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- СВЯЗИ ---
	location: Mapped["Location"] = relationship(back_populates="lights")
	token: Mapped["Token | None"] = relationship()

	def __repr__(self) -> str:
		source = self.token.character.name if self.token and self.token.character else "Ambient"
		return f"<LightSource(id={self.id}, src={source}, r={self.vision_radius})>"


