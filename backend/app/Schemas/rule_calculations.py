# backend/app/Schemas/rule_calculations.py

from Config.imports import (BaseModel, ConfigDict, Field, Literal, model_validator, re)


VALUE_LIMIT = 1_000_000_000

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

	# Целые константы или ссылки:
	# level
	# attribute.dex
	# modifier.dex
	# stat.other_value
	arguments: list[int | str] = Field(
		min_length=1,
		max_length=16,
	)

	@model_validator(mode="after")
	def validate_formula(self):
		if self.operation in {
			"subtract", "floor_div", "ceil_div",
		} and len(self.arguments) != 2:
			raise ValueError(
				"Вычитание и деление требуют ровно два аргумента"
			)

		for argument in self.arguments:
			if isinstance(argument, int):
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

		if (
				self.operation in {"floor_div", "ceil_div"}
				and self.arguments[1] == 0
		):
			raise ValueError("Деление на ноль")

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

			for argument in definition.formula.arguments:
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

	arguments: list[int | str]
	resolved_arguments: list[int]
	value: int

class AttributePreviewResult(CalculationModel):
	level: int
	attributes: dict[str, int]
	modifiers: dict[str, int]
	derived: dict[str, int]
	steps: list[CalculationStep]