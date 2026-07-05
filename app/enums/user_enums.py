# app/database/models.py

from Config.imports import enum


class Role_enums(enum.Enum):
	"""
	Перечисление всех возможных действий для логирования.
	Использование str, enum.Enum позволяет хранить значения в БД как строки.
	"""
	ADMIN = "admin"
	MASTER = "master"
	PLAYER = "player"

	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value