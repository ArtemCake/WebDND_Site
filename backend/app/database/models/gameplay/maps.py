# backend/app/models/gameplay/maps.py

"""Модели карт, слоев и гексов."""

from Config.imports import (String, Text, Integer, Boolean, DateTime, ForeignKey,
				Mapped, mapped_column, relationship, JSONB, text, datetime, PG_UUID,
				datetime, uuid4, Float, ARRAY)
from backend.app.database.database import Base


# --- КАРТЫ КАМПАНИИ ---
class CampaignMap(Base):
	"""
	Игровая карта.
	Реализует требование ТЗ о генерации карт мастером из пресетов или загрузке изображений.
	"""
	__tablename__ = "campaign_maps"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	game_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
	session_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
	title: Mapped[str] = mapped_column(String(255), nullable=False)
	map_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'image_upload', 'procedural_generation'
	background_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
	grid_settings_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	# {"cell_size": 100, "type": "hex", "color": "#333"}
	fog_of_war_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	lighting_model: Mapped[str] = mapped_column(String(20), nullable=False, server_default="basic") # 'basic', 'advanced_3d'
	is_active_in_session: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	game: Mapped["Game"] = relationship("Game", back_populates="campaign_maps")
	session: Mapped["Session"] = relationship("Session", back_populates="maps")
	layers: Mapped[list["MapLayer"]] = relationship("MapLayer", back_populates="map", cascade="all, delete-orphan")
	tokens: Mapped[list["Token"]] = relationship("Token", back_populates="current_map", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<CampaignMap(id='{self.id}', title='{self.title}')>"

# --- СЛОИ КАРТЫ ---
class MapLayer(Base):
	"""
	Визуальный слой карты.
	Реализует требование ТЗ о разделении Террейна, Объектов и Освещения.
	"""
	__tablename__ = "map_layers"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	map_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaign_maps.id", ondelete="CASCADE"), nullable=False, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'Terrain', 'Lighting', 'Tokens'
	z_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0") # Порядок отрисовки
	opacity: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
	is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	layer_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'raster_image', 'vector_tiles', 'dynamic_light'
	data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# Для vector-слоев здесь хранятся H3 индексы с метаданными
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	map: Mapped["CampaignMap"] = relationship("CampaignMap", back_populates="layers")
	hexes: Mapped[list["MapHex"]] = relationship("MapHex", back_populates="layer", cascade="all, delete-orphan")
	objects: Mapped[list["MapObject"]] = relationship("MapObject", back_populates="layer", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<MapLayer(id='{self.id}', type='{self.layer_type}', z={self.z_index})>"

# --- ГЕКСЫ КАРТЫ ---
class MapHex(Base):
	"""
	Процедурный гекс карты.
	Реализует требование ТЗ о процедурной генерации местности, где каждое поле карты — это гекс.
	Использует систему индексации Uber H3 для сверхбыстрого поиска соседей и зон видимости.
	"""
	__tablename__ = "map_hexes"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	layer_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("map_layers.id", ondelete="CASCADE"), nullable=False, index=True)
	h3_index: Mapped[str] = mapped_column(String(15), nullable=False, unique=True) # Индекс H3 (например, 8928307fffffffff)
	terrain_type_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("item_types.id"), nullable=True, index=True)
	elevation: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Высота в метрах/футах
	is_visible_to_players: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False) # Для динамического тумана войны
	explored_by_players: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Память игрока
	data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"cover": true, "difficult_terrain": true, "water_depth": 5}
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	layer: Mapped["MapLayer"] = relationship("MapLayer", back_populates="hexes")
	terrain_type: Mapped["ItemType"] = relationship("ItemType") # Ссылка на справочник типов предметов как террейна

	def __repr__(self) -> str:
		return f"<MapHex(id='{self.id}', h3='{self.h3_index}')>"

# --- ОБЪЕКТЫ НА КАРТЕ ---
class MapObject(Base):
	"""
	Интерактивный объект на карте.
	Реализует требование ТЗ о загрузке предметов мастером и их размещении на сцене.
	"""
	__tablename__ = "map_objects"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	layer_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("map_layers.id", ondelete="CASCADE"), nullable=False, index=True)
	object_template_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True, index=True)
	owner_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	# Позиция в локальных координатах карты (пиксели или юниты сетки)
	position_x: Mapped[float] = mapped_column(Float, nullable=False)
	position_y: Mapped[float] = mapped_column(Float, nullable=False)
	z_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Слой отрисовки внутри Layer
	rotation_deg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
	scale: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
	is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Защита от случайного сдвига
	is_visible_to_players: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"is_interactive": true, "hp": 50, "locked_door": true}
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	layer: Mapped["MapLayer"] = relationship("MapLayer", back_populates="objects")
	template: Mapped["Equipment"] = relationship("Equipment") # Предмет из справочника снаряжения
	owner: Mapped["User"] = relationship("User", back_populates="uploaded_assets") # Если это загруженная картинка

	def __repr__(self) -> str:
		return f"<MapObject(id='{self.id}', x={self.position_x}, y={self.position_y})>"

# --- ТОКЕНЫ (ФИШКИ) ---
class Token(Base):
	"""
	Игровая фишка персонажа, НПС или существа на карте.
	Реализует требование ТЗ о динамическом тумане войны и видимых состояниях.
	"""
	__tablename__ = "tokens"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
	current_map_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaign_maps.id", ondelete="SET NULL"), nullable=True, index=True)
	# Ссылка на сущность (может быть игроком через sheet или монстром из бестиария)
	character_sheet_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("character_sheets.id", ondelete="SET NULL"), nullable=True, index=True)
	npc_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="SET NULL"), nullable=True, index=True)
	owner_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	# Визуальное представление
	image_url: Mapped[str] = mapped_column(String(1000), nullable=False)
	display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
	# Позиция на сетке
	grid_x: Mapped[int] = mapped_column(Integer, nullable=False)
	grid_y: Mapped[int] = mapped_column(Integer, nullable=False)
	elevation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	rotation_deg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
	# Боевые статы (снапшот для боя)
	hp_current: Mapped[int] = mapped_column(Integer, nullable=False)
	hp_max: Mapped[int] = mapped_column(Integer, nullable=False)
	conditions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"prone": true, "poisoned": {"dc": 13}, "invisible": true}
	is_visible_to_players: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	controlled_by_ids: Mapped[list[PG_UUID] | None] = mapped_column( ARRAY(PG_UUID(as_uuid=True)), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	session: Mapped["Session"] = relationship("Session", back_populates="tokens")
	map: Mapped["CampaignMap"] = relationship("CampaignMap", back_populates="tokens")
	owner: Mapped["User"] = relationship("User")
	character_sheet: Mapped["CharacterSheet"] = relationship("CharacterSheet")
	npc: Mapped["NPC"] = relationship("NPC")

	def __repr__(self) -> str:
		return f"<Token(id='{self.id}', name='{self.display_name or 'Unnamed'}', x={self.grid_x})>"

# --- ЗОНЫ ПРОСТРАНСТВЕННОГО АУДИО ---
class SpatialAudioZone(Base):
	"""
	Зона распространения звука на карте.
	Реализует требование ТЗ об актуальных технических решениях 2026 года в области VTT.
	Позволяет игрокам слышать звуки только с определенного расстояния и через преграды.
	"""
	__tablename__ = "spatial_audio_zones"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	map_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaign_maps.id", ondelete="CASCADE"), nullable=False, index=True)
	creator_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	# Геометрия зоны (GeoJSON полигон или массив H3 индексов)
	geometry_geojson: Mapped[dict] = mapped_column(JSONB, nullable=False)
	# {"type": "Polygon", "coordinates": [[[x1,y1], [x2,y2], ...]]}
	sound_source_url: Mapped[str] = mapped_column(String(1000), nullable=False) # Ссылка на .wav/.ogg файл
	volume_db: Mapped[float] = mapped_column(Float, default=0.0, nullable=False) # Громкость в децибелах
	falloff_curve: Mapped[str] = mapped_column(String(20), nullable=False, server_default="logarithmic")
	# 'linear', 'inverse', 'logarithmic'
	max_distance: Mapped[int] = mapped_column(Integer, nullable=False) # В футах/секундах сетки
	acoustic_material: Mapped[str | None] = mapped_column(String(50), nullable=True)
	# 'stone', 'wood', 'water' - влияет на эхо и поглощение частот
	is_looping: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	is_muted_by_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	map: Mapped["CampaignMap"] = relationship("CampaignMap")
	creator: Mapped["User"] = relationship("User")

	def __repr__(self) -> str:
		return f"<SpatialAudioZone(id='{self.id}', source='{self.sound_source_url}')>"