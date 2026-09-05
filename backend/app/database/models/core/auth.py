# backend/app/models/core/auth.py

"""Модели ролей пользователей и прав доступа."""

from Config.imports import (String, Integer, ForeignKey, PG_UUID,
	Mapped, mapped_column, relationship, datetime, DateTime, text)
from backend.app.database.database import Base


class Role(Base):
	"""
	Справочник ролей системы.
	Уровень (level) определяет приоритет прав: чем выше число, тем выше приоритет.
	Соответствует ТЗ: 0 – Игрок, 1 – Мастер, 2 – Редактор, 3 - Администратор.
	"""
	__tablename__ = "roles"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
	level: Mapped[int] = mapped_column(Integer, nullable=False, comment="0-Игрок, 1-Мастер, 2-Редактор, 3-Админ")

	users: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<Role(id={self.id}, name='{self.name}', level={self.level})>"

class UserRole(Base):
	"""
	Промежуточная таблица для связи Many-to-Many между пользователями и ролями.
	Реализует логику из ТЗ: у пользователя может быть несколько ролей,
	функционал доступен по самой высокой роли.
	"""
	__tablename__ = "user_roles"

	user_id: Mapped[PG_UUID] = mapped_column(
		PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
	)
	role_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
	)
	assigned_at: Mapped[datetime | None] = mapped_column( DateTime(timezone=True), nullable=True, server_default=text("now()") )

	user: Mapped["User"] = relationship("User", back_populates="roles")
	role: Mapped["Role"] = relationship("Role", back_populates="users")

	def __repr__(self) -> str:
		return f"<UserRole(user_id='{self.user_id}', role_id={self.role_id})>"