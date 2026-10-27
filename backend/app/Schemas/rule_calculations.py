# backend/app/Schemas/rule_calculations.py

from __future__ import annotations
from Config.imports import (BaseModel, ConfigDict, Field, Literal, model_validator, re)


VALUE_LIMIT = 1_000_000_000

# Ограничения сложности одной формулы.
# Корневая операция считается первым уровнем.
MAX_FORMULA_DEPTH = 8

# Считаются все операции, числа и ссылки внутри одной формулы.
MAX_FORMULA_NODES = 256


CalculationOperation = Literal[
	"sum",
	"subtract",
	"multiply",
	"floor_div",
	"ceil_div",
	"min",
	"max",
]

class CalculationModel(BaseModel):
	model_config = ConfigDict(
		extra="forbid",
		strict=True,
		validate_default=True,
	)

class AttributeDefinition(CalculationModel):
	label: str = Field(min_length=1, max_length=100)

	# Технический диапазон. Конкретная система может его сузить.
	min_value: int = Field(default=-1000, ge=-1000, le=1000)
	max_value: int = Field(default=1000, ge=-1000, le=1000)

	@model_validator(mode="after")
	def validate_definition(self):
		if not self.label.strip():
			raise ValueError("Название характеристики не может быть пустым")

		if self.min_value > self.max_value:
			raise ValueError(
				"Минимум характеристики не может превышать максимум"
			)

		return self

class StatFormula(CalculationModel):
	operation: CalculationOperation

	# Аргумент:
	# - целое число;
	# - ссылка на источник;
	# - вложенная формула той же структуры.
	arguments: list[int | str | StatFormula] = Field(
		min_length=1,
		max_length=16,
	)

	@model_validator(mode="before")
	@classmethod
	def validate_complexity(cls, raw):
		"""Проверить размер дерева до рекурсивного разбора Pydantic."""
		stack = [(raw, 1)]
		nodes = 0

		while stack:
			current, depth = stack.pop()
			nodes += 1

			if nodes > MAX_FORMULA_NODES:
				raise ValueError(
					"Формула содержит слишком много элементов"
				)

			if isinstance(current, cls):
				arguments = current.arguments
			elif isinstance(current, dict):
				arguments = current.get("arguments")
			else:
				# Числа и ссылки тоже учитываются в размере,
				# но не увеличивают глубину операций.
				continue

			if depth > MAX_FORMULA_DEPTH:
				raise ValueError(
					"Превышена допустимая глубина вложенных вычислений"
				)

			if isinstance(arguments, list):
				stack.extend(
					(argument, depth + 1)
					for argument in arguments
				)

		return raw

	@model_validator(mode="after")
	def validate_formula(self):
		if self.operation in {
			"subtract", "floor_div", "ceil_div",
		} and len(self.arguments) != 2:
			raise ValueError(
				"Вычитание и деление требуют ровно два аргумента"
			)

		for argument in self.arguments:
			if isinstance(argument, StatFormula):
				# Вложенная операция проходит собственную проверку.
				continue

			if type(argument) is int:
				if abs(argument) > VALUE_LIMIT:
					raise ValueError(
						"Константа формулы выходит за допустимый диапазон"
					)
				continue

			if argument == "level":
				continue

			if not re.fullmatch(
					r"(attribute|modifier|stat)\.[a-z][a-z0-9_]{0,39}",
					argument,
			):
				raise ValueError(
					f"Недопустимая ссылка в формуле: {argument}"
				)

		if self.operation in {"floor_div", "ceil_div"}:
			denominator = self.arguments[1]

			if type(denominator) is int and denominator == 0:
				raise ValueError("Деление на ноль")

		return self

	def iter_leaf_arguments(self):
		"""Все числа и ссылки, включая вложенные вычисления."""
		stack = list(reversed(self.arguments))

		while stack:
			argument = stack.pop()

			if isinstance(argument, StatFormula):
				stack.extend(reversed(argument.arguments))
			else:
				yield argument

def validate_modifier_formula(formula: StatFormula | None) -> None:
	"""Формула модификатора использует только собственное значение.

	attribute.value — локальная ссылка на значение характеристики,
	модификатор которой сейчас рассчитывается.
	"""

	if formula is None:
		return

	for argument in formula.iter_leaf_arguments():
		if type(argument) is int:
			continue

		if argument != "attribute.value":
			raise ValueError(
				"В формуле модификатора разрешены только числа "
				"и значение этой характеристики"
			)

class AttributeDefinition(CalculationModel):
	label: str = Field(min_length=1, max_length=100)

	# Технический диапазон. Конкретная система может его сузить.
	min_value: int = Field(default=-1000, ge=-1000, le=1000)
	max_value: int = Field(default=1000, ge=-1000, le=1000)

	# None — использовать общее правило системы.
	modifier_formula: StatFormula | None = None

	@model_validator(mode="after")
	def validate_definition(self):
		if not self.label.strip():
			raise ValueError(
				"Название характеристики не может быть пустым"
			)

		if self.min_value > self.max_value:
			raise ValueError(
				"Минимум характеристики не может превышать максимум"
			)

		validate_modifier_formula(self.modifier_formula)

		return self

class DerivedStat(CalculationModel):
	label: str = Field(min_length=1, max_length=100)
	formula: StatFormula

	@model_validator(mode="after")
	def validate_label(self):
		if not self.label.strip():
			raise ValueError(
				"Название вычисляемого показателя не может быть пустым"
			)

		return self

class AttributeCalculations(CalculationModel):
	attributes: dict[str, AttributeDefinition] = Field(
		min_length=1,
		max_length=40,
	)

	derived: dict[str, DerivedStat] = Field(
		default_factory=dict,
		max_length=128,
	)

	def calculation_order(self) -> list[str]:
		"""Проверяет ссылки и возвращает порядок вычислений."""

		for code in (*self.attributes, *self.derived):
			if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", code):
				raise ValueError(
					f"Недопустимый код показателя: {code}"
				)

		dependencies: dict[str, set[str]] = {}

		for code, definition in self.derived.items():
			required = set()

			for argument in definition.formula.iter_leaf_arguments():
				if isinstance(argument, int) or argument == "level":
					continue

				namespace, target = argument.split(".", 1)

				if namespace in {"attribute", "modifier"}:
					if target not in self.attributes:
						raise ValueError(
							f"Показатель {code}: неизвестная "
							f"характеристика {target}"
						)
				elif target not in self.derived:
					raise ValueError(
						f"Показатель {code}: неизвестный "
						f"вычисляемый показатель {target}"
					)
				else:
					required.add(target)

			dependencies[code] = required

		order = []

		while dependencies:
			ready = sorted(
				code
				for code, required in dependencies.items()
				if not required
			)

			if not ready:
				problematic = ", ".join(sorted(dependencies))
				raise ValueError(
					"Циклическая зависимость вычисляемых "
					f"показателей: {problematic}"
				)

			for code in ready:
				order.append(code)
				del dependencies[code]

			for required in dependencies.values():
				required.difference_update(ready)

		return order

	@model_validator(mode="after")
	def validate_graph(self):
		self.calculation_order()
		return self

class CalculationStep(CalculationModel):
	code: str

	operation: Literal[
		"identity",
		"sum",
		"subtract",
		"multiply",
		"floor_div",
		"ceil_div",
		"min",
		"max",
	]

	arguments: list[int | str | StatFormula]
	resolved_arguments: list[int]
	value: int

class AttributePreviewResult(CalculationModel):
	level: int
	attributes: dict[str, int]
	modifiers: dict[str, int]
	derived: dict[str, int]
	steps: list[CalculationStep]