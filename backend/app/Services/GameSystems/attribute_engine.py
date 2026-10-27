# backend/app/Services/GameSystems/attribute_engine.py

from backend.app.Schemas.game_rules import AttributePreviewInput
from backend.app.Schemas.rule_calculations import (AttributePreviewResult)
from backend.app.Services.GameSystems.formula_engine import (evaluate_formula)
from backend.app.Services.GameSystems.rules_engine import (calculate_attribute_modifier)


def evaluate_attributes(data: AttributePreviewInput) -> AttributePreviewResult:
	"""Чистый предпросмотр без бросков и изменения состояния."""

	# Экземпляры Pydantic могли быть изменены после валидации.
	data = AttributePreviewInput.model_validate(
		data.model_dump(mode="python"),
	)

	rules = data.rules
	config = rules.calculations

	if rules.schema_version != 2 or config is None:
		raise ValueError(
			"Предпросмотр характеристик требует профиль версии 2"
		)

	if data.level > rules.max_level:
		raise ValueError(
			f"Уровень должен быть от 1 до {rules.max_level}"
		)

	expected = set(config.attributes)
	received = set(data.attributes)

	if expected != received:
		missing = sorted(expected - received)
		unknown = sorted(received - expected)
		problems = []

		if missing:
			problems.append(
				"не заданы характеристики: " + ", ".join(missing)
			)

		if unknown:
			problems.append(
				"неизвестные характеристики: " + ", ".join(unknown)
			)

		raise ValueError("; ".join(problems))

	modifiers = {}
	derived = {}
	steps = []

	context = {
		"level": data.level,
	}

	for code, definition in config.attributes.items():
		value = data.attributes[code]

		if not definition.min_value <= value <= definition.max_value:
			raise ValueError(
				f"Характеристика {code}: допустимый диапазон "
				f"от {definition.min_value} до {definition.max_value}"
			)

		modifier = calculate_attribute_modifier(
			rules,
			value,
			code,
			steps=steps,
		)

		modifiers[code] = modifier
		context[f"attribute.{code}"] = value
		context[f"modifier.{code}"] = modifier

	for code in config.calculation_order():
		formula = config.derived[code].formula

		value = evaluate_formula(
			formula=formula,
			context=context,
			steps=steps,
			code=f"stat.{code}",
		)

		derived[code] = value
		context[f"stat.{code}"] = value

	return AttributePreviewResult(
		level=data.level,
		attributes=dict(data.attributes),
		modifiers=modifiers,
		derived=derived,
		steps=steps,
	)