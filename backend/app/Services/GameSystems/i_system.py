# backend/app/Services/GameSystems/admin_service.py

from Config.imports import (ABC, abstractmethod, Any)


class ISystem(ABC):
	"""
	Общий интерфейс игровой системы (D&D 5e, Pathfinder и т.д.).
	Инкапсулирует все формулы и правила конкретной системы, чтобы игровое
	ядро (роутеры, сервисы персонажей/лобби) не знало деталей расчётов
	и могло работать с любой системой одинаково.
	"""

	slug: str  # должен совпадать с GameSystem.slug в БД ('dnd-5e', 'pathfinder-2e')

	@abstractmethod
	def calculate_ability(self, base_value: int, bonus: int) -> tuple[int, int]:
		"""Возвращает (final_value, modifier) для одной характеристики."""
		raise NotImplementedError

	@abstractmethod
	def calculate_proficiency_bonus(self, level: int) -> int:
		"""Бонус мастерства по уровню персонажа."""
		raise NotImplementedError

	@abstractmethod
	def default_stats_json(self) -> dict[str, Any]:
		"""Структура stats_json по умолчанию для нового листа этой системы."""
		raise NotImplementedError

	@abstractmethod
	def default_saves_json(self) -> dict[str, Any]:
		raise NotImplementedError

	@abstractmethod
	def default_skills_json(self) -> dict[str, Any]:
		raise NotImplementedError

	@abstractmethod
	def validate_stats(self, stats_json: dict[str, Any]) -> dict[str, Any]:
		"""Проверяет состав ключей stats_json; бросает ValueError при несовпадении."""
		raise NotImplementedError

	@abstractmethod
	def validate_saves(self, saves_json: dict[str, Any]) -> dict[str, Any]:
		raise NotImplementedError

	@abstractmethod
	def validate_skills(self, skills_json: dict[str, Any]) -> dict[str, Any]:
		raise NotImplementedError