# app/database/models.py

from Config.imports import (Column, Integer, String, Text, Boolean, Enum, SQLEnum,
                            DateTime, func, relationship, ForeignKey, datetime)
from app.database.database import Base
from app.enums.log_enums import LogLevelEnum, LogAction
from app.enums.user_enums import Role_enums


class Character(Base):
	__tablename__ = "characters"

	id = Column(Integer, primary_key=True, index=True)

	# Основные поля персонажа
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	name = Column(String(100), nullable=False)
	race = Column(String(50))
	character_class = Column(String(50)) # Класс нельзя называть 'class'
	level = Column(Integer, default=1)

	# Характеристики (статы)
	strength = Column(Integer, default=10)
	dexterity = Column(Integer, default=10)
	constitution = Column(Integer, default=10)
	intelligence = Column(Integer, default=10)
	wisdom = Column(Integer, default=10)
	charisma = Column(Integer, default=10)

	# Биография
	background = Column(Text)

	user = relationship("User", back_populates="characters")

	def __repr__(self):
		return f"<Character(id={id}, name='{self.name}', lvl={self.level})>"

class UserLog(Base):
	"""
	Таблица для логирования действий пользователей.
	Хранит информацию о том, кто, что и когда сделал.
	"""
	__tablename__ = "user_logs"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	action = Column(
		SQLEnum(LogAction, literal_bindparam=True),
		nullable=False,
		index=True
	)
	description = Column(Text, nullable=True)   # Подробности, например: "Создал пресет 'Стандартный'"
	log_level = Column(
		SQLEnum(LogLevelEnum, literal_bindparam=True), # Используем наш Enum
		nullable=False,
		default=LogLevelEnum.INFO, # По умолчанию лог будет информационным
		index=True # Создаем индекс для быстрой фильтрации
	)
	timestamp = Column(DateTime, default=datetime.utcnow, index=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

	# Связь с пользователем
	user = relationship("User", back_populates="logs")
	def __repr__(self):
		return f"<user_logs(user_id='{self.user_id}', log_level='{self.log_level}')>"

class AppLog(Base):
	"""
	Таблица для хранения системных логов и действий пользователей.
	В отличие от UserLog, здесь хранится username, а не user_id, чтобы логировать
	события регистрации и входа, когда пользователя в БД еще нет или он не авторизован.
	"""
	__tablename__ = "app_logs"

	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(50), nullable=True, index=True)
	action = Column(
		SQLEnum(LogAction, literal_bindparam=True),
		nullable=False,
		index=True
	)
	description = Column(Text, nullable=True)   # Подробности
	timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
	log_level = Column(
		SQLEnum(LogLevelEnum, literal_bindparam=True), # Используем наш Enum
		nullable=False,
		default=LogLevelEnum.INFO, # По умолчанию лог будет информационным
		index=True # Создаем индекс для быстрой фильтрации
	)

class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)

	username = Column(String(50), unique=True, nullable=False, index=True) # Логин
	hashed_password = Column(String(255), nullable=False) # ХЕШ пароля (не сам пароль!)

	is_active = Column(Boolean(), default=True) # Заблокирован ли аккаунт
	role = Column(Enum(Role_enums), default=Role_enums.PLAYER, nullable=False) # Роль пользователя

	gdpr_consent = Column(Boolean(), default=False) # Согласие на обработку персональных данных

	created_at = Column(DateTime(timezone=True), server_default=func.now()) # Дата регистрации

	# Связь один-ко-многим: У одного пользователя много персонажей
	characters = relationship("Character", back_populates="user",
	                          foreign_keys="Character.user_id",
	                          passive_deletes=True)

	logs = relationship("UserLog", back_populates="user",
	                    order_by=UserLog.timestamp.desc()
	                    , passive_deletes=True)

	def __repr__(self):
		return f"<User(username='{self.username}', role='{self.role}')>"