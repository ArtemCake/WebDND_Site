# app/enums/person_enums.py

from Config.imports import enum


class ItemCategory(enum.Enum):
	WEAPON = "weapon"
	ARMOR = "armor"
	GEAR = "gear" # Свитки, зелья
	WONDROUS_ITEM = "wondrous_item"
	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value

class ProtectionType(enum.Enum):
	RESISTANCE = "resistance"
	VULNERABILITY = "vulnerability"
	IMMUNITY = "immunity"
	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value

class PreparationStatus(enum.Enum):
	KNOWN = "known"
	PREPARED = "prepared"
	BOTH = "both"
	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value

class ProficiencyType(enum.Enum):
	WEAPON = "weapon"
	ARMOR = "armor"
	TOOL = "tool"
	def __str__(self) -> str:
		"""Позволяет использовать f-строки и print() для получения значения."""
		return self.value