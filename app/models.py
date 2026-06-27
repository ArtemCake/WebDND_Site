# app/models.py

from Config.imports import (Column, Integer, String, Text, DateTime, datetime)
from app.database.database import Base

class Character(Base):
	"""
	Модель персонажа для хранения в базе данных.
	Наследуется от Base, который мы настроим в database.py.
	"""
	__tablename__ = "characters"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, index=True) # ID пользователя-владельца

	name = Column(String(50), nullable=False)
	race = Column(String(50))
	character_class = Column(String(50)) # 'class' - зарезервированное слово в Python
	level = Column(Integer, default=1)
	background = Column(Text) # Предыстория персонажа

	created_at = Column(DateTime, default=datetime.datetime.utcnow)

	def __repr__(self):
		return f"<Character(name='{self.name}', class='{self.character_class}')>"