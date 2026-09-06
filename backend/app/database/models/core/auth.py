# backend/app/models/core/auth.py

"""Модели ролей пользователей и прав доступа."""

from Config.imports import (String, Integer, ForeignKey, PG_UUID,
	Mapped, mapped_column, relationship, datetime, DateTime, text)
from backend.app.database.database import Base
from backend.app.enums.enums_BD import SystemRole


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

	assigned_at: Mapped[datetime | None] = mapped_column( DateTime(timezone=True), nullable=True, server_default=text("now()") )

	user: Mapped["User"] = relationship("User", back_populates="roles")
	role: Mapped[str] = mapped_column( SystemRole.pg_enum_type(), primary_key=True, nullable=False )

	def __repr__(self) -> str:
		return f"<UserRole(user_id='{self.user_id}', role_id={self.role_id})>"