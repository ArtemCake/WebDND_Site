# backend/app/Services/GameSystems/formula_engine.py

from backend.app.Schemas.rule_calculations import (CalculationStep, StatFormula, VALUE_LIMIT)


def bounded(value: int) -> int:
	if abs(value) > VALUE_LIMIT:
		raise ValueError(
			"Результат вычисления выходит за допустимый диапазон"
		)

	return value

def apply_operation(operation: str, values: list[int]) -> int:
	if operation == "sum":
		return bounded(sum(values))

	if operation == "subtract":
		return bounded(values[0] - values[1])

	if operation == "multiply":
		result = 1

		for value in values:
			result = bounded(result * value)

		return result

	if operation in {"floor_div", "ceil_div"}:
		numerator, denominator = values

		if denominator == 0:
			raise ValueError("Деление на ноль")

		if operation == "floor_div":
			return bounded(numerator // denominator)

		return bounded(-((-numerator) // denominator))

	if operation == "min":
		return bounded(min(values))

	if operation == "max":
		return bounded(max(values))

	raise ValueError("Неизвестная операция вычисления")

def evaluate_formula(formula: StatFormula, context: dict[str, int], steps: list[CalculationStep] | None, code: str) -> int:
	"""Вычислить дочерние операции, затем родительскую.

	steps=None — выполнить расчёт без формирования пояснения.
	"""

	resolved = []

	for index, argument in enumerate(formula.arguments):
		if isinstance(argument, StatFormula):
			value = evaluate_formula(
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

		resolved.append(bounded(value))

	try:
		value = apply_operation(
			formula.operation,
			resolved,
		)
	except ValueError as exc:
		raise ValueError(
			f"Вычисление {code}: {exc}"
		) from exc

	if steps is not None:
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