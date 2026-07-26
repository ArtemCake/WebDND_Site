# app/database/models/lore_models.py

from Config.imports import (
	Integer, String, Text, DateTime, func, Boolean, JSONB, ForeignKey,
	relationship, datetime, Mapped, mapped_column)
from app.database.database import Base


class LoreArticle(Base):
	"""
	Статья мира. Это может быть описание города, гильдии, NPC или заклинания хоумбрю.
	Поддерживает иерархию (дерево статей) через parent_id.
	"""
	__tablename__ = "lore_articles"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	campaign_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("campaigns.id", ondelete="CASCADE"),
		nullable=False,
		index=True
	)

	# Иерархия документов
	parent_id: Mapped[int | None] = mapped_column(
		ForeignKey("lore_articles.id", ondelete="CASCADE"),
		nullable=True,
		index=True
	)

	title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
	slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True) # Для URL /lore/city-of-brass

	content_html: Mapped[str] = mapped_column(Text, nullable=False) # Рендер из WYSIWYG редактора
	content_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # Сырой JSON блоков (для ProseMirror/Tiptap)

	excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True) # Превью для списка статей

	article_type: Mapped[str] = mapped_column(String(50), default="ARTICLE") # ARTICLE, NPC, ITEM_BREW, SPELL_BREW

	is_private_dm_only: Mapped[bool] = mapped_column(Boolean(), default=False) # Видно только Мастеру
	allow_player_edits: Mapped[bool] = mapped_column(Boolean(), default=False)

	cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

	# --- СВЯЗИ ---
	campaign: Mapped["Campaign"] = relationship(back_populates="lore_articles")

	author: Mapped["User | None"] = relationship() # Если нужно знать автора конкретной правки

	children: Mapped[list["LoreArticle"]] = relationship(
		back_populates="parent",
		cascade="all, delete-orphan",
		passive_deletes=True
	)

	parent: Mapped["LoreArticle | None"] = relationship(
		remote_side=[id],
		back_populates="children"
	)

	tags: Mapped[list["LoreTag"]] = relationship(
		secondary="article_tags",
		back_populates="articles",
		cascade="all"
	)

	def __repr__(self) -> str:
		return f"<LoreArticle(id={self.id}, title='{self.title}', type={self.article_type})>"

class LoreTag(Base):
	"""
	Тег для фильтрации статей (например: #География, #НПС, #Квесты).
	"""
	__tablename__ = "lore_tags"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
	color_hex: Mapped[str] = mapped_column(String(7), default="#6c757d") # Цвет метки в UI

	articles: Mapped[list[LoreArticle]] = relationship(
		secondary="article_tags",
		back_populates="tags"
	)

# Связующая таблица Многие-ко-многим
class ArticleTagLink(Base):
	__tablename__ = "article_tags"

	article_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("lore_articles.id", ondelete="CASCADE"),
		primary_key=True
	)
	tag_id: Mapped[int] = mapped_column(
		Integer,
		ForeignKey("lore_tags.id", ondelete="CASCADE"),
		primary_key=True
	)