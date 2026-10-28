# backend/app/Services/GameSystems/rules_composition.py

"""Сборка расчётного профиля из основы и локальных изменений."""

from Config.imports import (Any, deepcopy)
from backend.app.Schemas.game_rules import RulesProfile


# Версия схемы и происхождение основы не являются домашними правилами.
# Их изменение потребует отдельного управляемого перехода.
OVERRIDABLE_FIELDS = frozenset({
	"attribute_mode",
	"attribute_codes",
	"modifier_offset",
	"modifier_divisor",
	"modifier_formula",
	"max_level",
	"proficiency_ranks",
	"checks",
	"calculations",
})

def compose_system_rules(base_rules: RulesProfile, overrides: dict[str, Any] | None = None) -> RulesProfile:
	"""
	Вернуть независимый, повторно проверенный итоговый профиль.

	Правила:
	- отсутствие поля означает наследование;
	- переданное поле заменяет значение основы целиком;
	- None является явным значением, а не удалением поля;
	- неизвестные и защищённые поля отклоняются;
	- исходный профиль и переопределения не изменяются.

	Функция не загружает публикацию, не проверяет права и не сохраняет
	результат. Эти обязанности остаются у вызывающего сервиса.
	"""
	if overrides is None:
		overrides = {}

	if not isinstance(overrides, dict):
		raise ValueError("Переопределения должны быть словарём")

	if any(not isinstance(key, str) for key in overrides):
		raise ValueError(
			"Названия переопределяемых полей должны быть строками"
		)

	forbidden = set(overrides) - OVERRIDABLE_FIELDS
	if forbidden:
		raise ValueError(
			"Недопустимые поля переопределений: "
			+ ", ".join(sorted(forbidden))
		)

	effective = deepcopy(base_rules.model_dump(mode="python"))
	effective.update(deepcopy(overrides))

	# Не используем model_copy(update=...):
	# обновления должны пройти проверки итогового профиля.
	return RulesProfile.model_validate(effective)