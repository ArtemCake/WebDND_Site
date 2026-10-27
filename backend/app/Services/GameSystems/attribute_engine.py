# backend/app/Services/GameSystems/attribute_engine.py

from backend.app.Schemas.game_rules import AttributePreviewInput
from backend.app.Schemas.rule_calculations import (AttributePreviewResult, CalculationStep, StatFormula, VALUE_LIMIT)
from backend.app.Services.GameSystems.rules_engine import (calculate_attribute_modifier)


def _bounded(value: int) -> int:
	if abs(value) > VALUE_LIMIT:
		raise ValueError(
			"Результат вычисления выходит за допустимый диапазон"
		)

	return value

def _apply_operation(operation: str, values: list[int]) -> int:
	if operation == "sum":
		return _bounded(sum(values))

	if operation == "subtract":
		return _bounded(values[0] - values[1])

	if operation == "multiply":
		result = 1

		for value in values:
			result = _bounded(result * value)

		return result

	if operation in {"floor_div", "ceil_div"}:
		numerator, denominator = values

		if denominator == 0:
			raise ValueError("Деление на ноль")

		if operation == "floor_div":
			return _bounded(numerator // denominator)

		return _bounded(-((-numerator) // denominator))

	if operation == "min":
		return min(values)

	if operation == "max":
		return max(values)

	raise ValueError("Неизвестная операция вычисления")

def _evaluate_formula(formula: StatFormula, context: dict[str, int], steps: list[CalculationStep], code: str) -> int:
	"""Вычислить дочерние операции, затем родительскую."""
	resolved = []

	for index, argument in enumerate(formula.arguments):
		if isinstance(argument, StatFormula):
			value = _evaluate_formula(
				formula=argument,
				context=context,
				steps=steps,
				code=f"{code}/{index}",
			)
		elif type(argument) is int:
			value = argument
		else:
			if argument not in context:
				raise ValueError(
					f"Недоступный источник: {argument}"
				)

			value = context[argument]

		resolved.append(value)

	try:
		value = _apply_operation(
			formula.operation,
			resolved,
		)
	except ValueError as exc:
		raise ValueError(
			f"Вычисление {code}: {exc}"
		) from exc

	steps.append(
		CalculationStep(
			code=code,
			operation=formula.operation,
			arguments=list(formula.arguments),
			resolved_arguments=resolved,
			value=value,
		)
	)

	return value

def evaluate_attributes(data: AttributePreviewInput) -> AttributePreviewResult:
	"""Чистый предпросмотр без бросков и изменения состояния."""

	# Проверяем повторно: экземпляры Pydantic могли быть изменены
	# после первоначальной валидации.
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

		modifier = _bounded(
			calculate_attribute_modifier(rules, value)
		)

		modifiers[code] = modifier
		context[f"attribute.{code}"] = value
		context[f"modifier.{code}"] = modifier

		if rules.attribute_mode == "modifier":
			operation = "identity"
			arguments = [f"attribute.{code}"]
			resolved = [value]
		else:
			operation = "floor_div"
			arguments = [
				value - rules.modifier_offset,
				rules.modifier_divisor,
				]
			resolved = list(arguments)

		steps.append(
			CalculationStep(
				code=f"modifier.{code}",
				operation=operation,
				arguments=arguments,
				resolved_arguments=resolved,
				value=modifier,
			)
		)

	for code in config.calculation_order():
		formula = config.derived[code].formula

		value = _evaluate_formula(
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