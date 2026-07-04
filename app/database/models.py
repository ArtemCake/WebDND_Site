# app/database/models.py

from Config.imports import Column, Integer, String, Text
from app.database.database import Base

class Character(Base):
	__tablename__ = "characters"

	id = Column(Integer, primary_key=True, index=True)

	# Основные поля персонажа
	user_id = Column(Integer, nullable=True, index=True) # Кто владелец (пока опционально)
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

	def __repr__(self):
		return f"<Character(id={id}, name='{self.name}', lvl={self.level})>"