# backend/app/models/gameplay/communication.py

"""Модели коммуникации: чаты и сообщения."""

from Config.imports import (String, Text, Boolean, DateTime, ForeignKey,
					Mapped, mapped_column, relationship, text, PG_UUID, uuid4, datetime)
from backend.app.database.database import Base


# --- ЧАТЫ ---
class Chat(Base):
	"""
	Канал связи внутри игровой сессии.
	Реализует требование ТЗ о наличии двух текстовых чатов (игровой и технический).
	"""
	__tablename__ = "chats"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
	name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'Общий', 'Технический'
	chat_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'player_chat' или 'gm_log'
	is_global: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	# False - приватный канал между выбранными участниками (реализуется через junction table при необходимости)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=text("now()"), server_default=text("now()"))
	session: Mapped["Session"] = relationship("Session", back_populates="chats")
	messages: Mapped[list["Message"]] = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Chat(id='{self.id}', type='{self.chat_type}')>"

# --- СООБЩЕНИЯ ---
class Message(Base):
	"""
	Единица текста в чате.
	Реализует требование ТЗ об удалении сообщений, приватных диалогах и скрытых бросках мастера.
	"""
	__tablename__ = "messages"

	id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
	chat_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
	sender_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	npc_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="SET NULL"), nullable=True, index=True)
	content: Mapped[str] = mapped_column(Text, nullable=False)
	# Для технических логов (#46) вместо текста может быть JSON-ссылка на бросок
	dice_roll_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dice_rolls.id", ondelete="SET NULL"), nullable=True, index=True)
	edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	deleted_for_players: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Требование ТЗ
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
	chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
	sender: Mapped["User"] = relationship("User", back_populates="chat_messages")
	npc: Mapped["NPC"] = relationship("NPC") # У НПС своя связь с сообщениями как у автора
	dice_roll: Mapped["DiceRoll"] = relationship("DiceRoll")

	def __repr__(self) -> str:
		return f"<Message(id='{self.id}', chat_id='{self.chat_id}', sender_id='{self.sender_id}')>"