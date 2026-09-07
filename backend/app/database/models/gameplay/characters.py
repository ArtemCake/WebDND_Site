# backend/app/models/gameplay/characters.py

"""Модели персонажей игроков и НПС в контексте игры."""

from Config.imports import (Mapped, mapped_column, relationship, JSONB, ARRAY, text,
							String, Text, Integer, Boolean, DateTime, ForeignKey, PG_UUID,
							datetime, uuid4)
from backend.app.database.database import Base


class Character(Base):
	"""
	Базовый шаблон персонажа игрока.
	Хранится у пользователя "в инвентаре" вне зависимости от конкретных игр.
	"""
	__tablename__ = "characters"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	# Владелец шаблона
	user_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

	# Ссылка на базовую версию из справочников билдинга
	race_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("races.id"))
	background_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("backgrounds.id"))

	# ХП и основные статы
	hp_max: Mapped[int] = mapped_column(Integer, nullable=False)
	experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	owner: Mapped["User"] = relationship("User", back_populates="characters")

# --- ЛИСТЫ ПЕРСОНАЖЕЙ ---
class CharacterSheet(Base):
	"""
	Версия персонажа внутри конкретной игровой сессии.
	Реализует требование ТЗ о сохранении изменений характеристик только внутри одной игры.
	"""
	__tablename__ = "character_sheets"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

	player_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
	)

	game_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
	)

	base_character_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True
	) # Ссылка на оригинал из глобального списка игрока

	npc_id: Mapped[PG_UUID | None] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="SET NULL"), nullable=True, index=True
	) # Если лист создан Мастером как заготовка

	version_note: Mapped[str | None] = mapped_column(Text, nullable=True) # 'Уровень 5, после боя с драконом'

	stats_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	# {"str": 16, "dex_mod": 2, "proficiency_bonus": 3}

	saves_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
	skills_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

	hp_current: Mapped[int] = mapped_column(Integer, nullable=False)
	hp_temp: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Временные HP

	death_saves_success: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	death_saves_failure: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

	conditions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")

	is_active_in_game: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))

	player: Mapped["User"] = relationship("User")
	game: Mapped["Game"] = relationship("Game", back_populates="party") # Косвенная связь через Party
	base_character: Mapped["Character"] = relationship("Character") # Глобальный персонаж пользователя
	npc: Mapped["NPC"] = relationship("NPC")
	inventory: Mapped[list["CharacterInventory"]] = relationship(
		"CharacterInventory", back_populates="sheet", cascade="all, delete-orphan"
	)
	tokens: Mapped[list["Token"]] = relationship("Token", back_populates="character_sheet", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<CharacterSheet(id='{self.id}', player_id='{self.player_id}')>"

# --- ИНВЕНТАРЬ ПЕРСОНАЖА ---
class CharacterInventory(Base):
	"""
	Конкретный экземпляр предмета в инвентаре персонажа.
	Реализует требование ТЗ о хранении количества, состояния и привязки предметов.
	"""
	__tablename__ = "character_inventory"

	sheet_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("character_sheets.id", ondelete="CASCADE"), primary_key=True
	)

	item_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True
	)

	quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

	is_attuned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Привязка магических предметов
	is_equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

	equipped_slot: Mapped[str | None] = mapped_column(String(30), nullable=True) # 'head', 'armor', 'ring_1'

	ammo_count: Mapped[int | None] = mapped_column(Integer, nullable=True) # Для стрел/болтов
	charges_current: Mapped[int | None] = mapped_column(Integer, nullable=True) # Для расходуемых палочек/свитков

	custom_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
	notes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default="{}")
	# {"cursed": true, "hidden_pocket": true}

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	npc_id: Mapped[PG_UUID | None] = mapped_column( PG_UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), nullable=True, index=True)
	owner_npc: Mapped["NPC"] = relationship("NPC", back_populates="inventory")

	sheet: Mapped["CharacterSheet"] = relationship("CharacterSheet", back_populates="inventory")
	item: Mapped["Equipment"] = relationship("Equipment") # Базовый справочник снаряжения

	def __repr__(self) -> str:
		return f"<CharacterInventory(sheet='{self.sheet_id}', item='{self.item.name if self.item else 'Unknown'}')>"