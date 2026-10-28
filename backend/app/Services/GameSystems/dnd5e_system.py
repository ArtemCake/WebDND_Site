# backend/app/Services/GameSystems/dnd5e_system.py

from Config.imports import (Any)
from backend.app.Services.GameSystems.i_system import ISystem


_ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
_SAVES = ("str", "dex", "con", "int", "wis", "cha")  # спасброски по тем же шести характеристикам
_PROFICIENCY_BY_LEVEL = (
	(5, 2), (9, 3), (13, 4), (17, 5), (21, 6),
)  # (верхняя граница уровня, бонус): 1-4 -> 2, 5-8 -> 3 и т.д.

class Dnd5eSystem(ISystem):
	slug = "dnd-5e"

	def calculate_ability(self, base_value: int, bonus: int) -> tuple[int, int]:
		final_value = base_value + bonus
		modifier = (final_value - 10) // 2
		return final_value, modifier

	def calculate_proficiency_bonus(self, level: int) -> int:
		for threshold, bonus in _PROFICIENCY_BY_LEVEL:
			if level < threshold:
				return bonus
		return _PROFICIENCY_BY_LEVEL[-1][1]

	def default_stats_json(self) -> dict[str, Any]:
		return {"proficiency_bonus": 2}

	def default_saves_json(self) -> dict[str, Any]:
		return {ability: False for ability in _SAVES}  # владение спасброском — bool на каждую характеристику

	def default_skills_json(self) -> dict[str, Any]:
		return {}  # владения навыками добавляются по мере выбора на фронте

	def validate_stats(self, stats_json: dict[str, Any]) -> dict[str, Any]:
		if "proficiency_bonus" not in stats_json:
			raise ValueError("stats_json должен содержать 'proficiency_bonus'")
		return stats_json

	def validate_saves(self, saves_json: dict[str, Any]) -> dict[str, Any]:
		unknown = set(saves_json) - set(_SAVES)
		if unknown:
			raise ValueError(f"saves_json содержит неизвестные ключи: {unknown}")
		return saves_json

	def validate_skills(self, skills_json: dict[str, Any]) -> dict[str, Any]:
		return skills_json  # навыки D&D 5e многочисленны, полный список сверим отдельно при необходимости
