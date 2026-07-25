# app/database/models/world.py

from Config.imports import (
	DateTime, func, Enum,
	Integer, String, Text, Boolean, ForeignKey,
	relationship, JSON, datetime, Mapped, mapped_column, backref
)
from app.database.database import Base
from app.enums.db_enums import EntityTypeEnum


class Campaign(Base):
	"""Кампания (серия приключений)"""
	__tablename__ = "campaigns"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	owner_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
	)

	name: Mapped[str] = mapped_column(String(100), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	home_rules_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	is_public: Mapped[bool] = mapped_column(Boolean(), default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- Связи ---
	owner: Mapped["User"] = relationship("User", back_populates="rules_created")
	sessions: Mapped[list["Session"]] = relationship(
		"Session",
		back_populates="campaign",
		cascade="all, delete-orphan",
		passive_deletes=True
	)
	characters: Mapped[list["CampaignCharacter"]] = relationship("CampaignCharacter", back_populates="campaign")
	quests: Mapped[list["Quest"]] = relationship("Quest", back_populates="campaign", cascade="all, delete-orphan")
	locations: Mapped[list["Location"]] = relationship("Location", back_populates="campaign", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Campaign(id={self.id}, name='{self.name}')>"

class Session(Base):
	"""Игровая сессия (одна встреча/вечер игры)"""
	__tablename__ = "sessions"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
	)

	date_played: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	summary: Mapped[str | None] = mapped_column(Text, nullable=True)
	xp_distributed: Mapped[int] = mapped_column(Integer, default=0)

	campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="sessions")

	def __repr__(self) -> str:
		return f"<Session(id={self.id}, date={self.date_played.date()})>"

class CampaignCharacter(Base):
	"""Связь персонажа и кампании (роль в кампании, статус, заметки мастера)"""
	__tablename__ = "campaign_characters"

	campaign_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
	)
	character_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
	)

	role_in_campaign: Mapped[str] = mapped_column(String(50), default="Player")
	joined_session: Mapped[int | None] = mapped_column(Integer, nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

	campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="characters")
	character: Mapped["Character"] = relationship("Character")

	def __repr__(self) -> str:
		return f"<CampaignCharacter(camp={self.campaign_id}, char={self.character_id})>"

class Quest(Base):
	"""Квестовый движок."""
	__tablename__ = "quests"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
	)
	location_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
	)
	issuer_faction_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
	)

	title: Mapped[str] = mapped_column(String(150), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	reward_xp: Mapped[int] = mapped_column(Integer, default=0)
	reward_cp: Mapped[int] = mapped_column(Integer, default=0)
	status: Mapped[str] = mapped_column(String(20), default='active')
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- Связи ---
	campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="quests")
	location: Mapped["Location | None"] = relationship("Location", back_populates="quests")
	issuer_faction: Mapped["Organization | None"] = relationship("Organization")
	objectives: Mapped[list["QuestObjective"]] = relationship(
		"QuestObjective",
		back_populates="quest",
		cascade="all, delete-orphan",
		order_by="QuestObjective.order_num",
		passive_deletes=True
	)
	party_assignments: Mapped[list["PartyQuestAssignment"]] = relationship("PartyQuestAssignment", back_populates="quest")

	def __repr__(self) -> str:
		return f"<Quest(id={self.id}, title='{self.title}', status='{self.status}')>"

class QuestObjective(Base):
	"""Конкретная цель квеста: убить X, найти Y, поговорить с Z."""
	__tablename__ = "quest_objectives"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	quest_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True
	)
	order_num: Mapped[int] = mapped_column(Integer, nullable=False)

	target_entity_type: Mapped[EntityTypeEnum | None] = mapped_column(Enum(EntityTypeEnum, native_enum=True, create_constraint=False), nullable=True)
	target_entity_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
	target_quantity: Mapped[int] = mapped_column(Integer, default=1)
	is_completed: Mapped[bool] = mapped_column(Boolean(), default=False)

	quest: Mapped["Quest"] = relationship("Quest", back_populates="objectives")

	def __repr__(self) -> str:
		tgt = self.target_entity_name or "Unknown Target"
		return f"<QuestObj(id={self.id}, '{tgt} x{self.target_quantity}', done={self.is_completed})>"

class PartyQuestAssignment(Base):
	"""Связь: какой персонаж или группа принял какой квест."""
	__tablename__ = "party_quest_assignments"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	quest_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True
	)
	character_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True
	)
	notes_dm: Mapped[str | None] = mapped_column(Text, nullable=True)

	quest: Mapped["Quest"] = relationship("Quest", back_populates="party_assignments")
	character: Mapped["Character | None"] = relationship("Character")

	def __repr__(self) -> str:
		actor = f"char={self.character_id}" if self.character_id else "group"
		return f"<PQAssign(id={self.id}, quest={self.quest_id}, {actor})>"

class Location(Base):
	"""Локации (города, подземелья, комнаты) с поддержкой вложенности (дерево)."""
	__tablename__ = "locations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
	)

	name: Mapped[str] = mapped_column(String(150), nullable=False)
	slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)

	parent_location_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
	)

	location_type: Mapped[str] = mapped_column(String(50), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	map_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
	biome_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

	# --- Связи ---
	campaign: Mapped["Campaign | None"] = relationship("Campaign", back_populates="locations")
	parent: Mapped["Location | None"] = relationship(
		"Location",
		remote_side=[id],
		backref=backref("children", lazy="dynamic"),
		post_update=True
	)
	lore_entries: Mapped[list["LoreEntry"]] = relationship("LoreEntry", back_populates="location")
	quests: Mapped[list["Quest"]] = relationship("Quest", back_populates="location")

	def __repr__(self) -> str:
		return f"<Location(id={self.id}, name='{self.name}')>"

class NoteCategory(Base):
	"""Категории заметок (Lore, Quest, Character, NPC, Location)"""
	__tablename__ = "note_categories"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
	color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True) # e.g., #FFD700

	def __repr__(self) -> str:
		return f"<NoteCategory(id={self.id}, name='{self.name}')>"

class LoreEntry(Base):
	"""Запись в базе знаний (бестиарий, история дома Нозеров, описание ритуала)."""
	__tablename__ = "lore_entries"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	author_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
	)
	location_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
	)

	title: Mapped[str] = mapped_column(String(150), nullable=False)
	content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
	entry_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
	tags_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	is_public_to_party: Mapped[bool] = mapped_column(Boolean(), default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	# --- Связи ---
	author: Mapped["User | None"] = relationship("User")
	location: Mapped["Location | None"] = relationship("Location", back_populates="lore_entries")

	def __repr__(self) -> str:
		loc_ref = f"loc={self.location_id}" if self.location_id else ""
		return f"<LoreEntry(id={self.id}, title='{self.title}', {loc_ref})>"