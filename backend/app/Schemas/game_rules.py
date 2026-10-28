# backend/app/Schemas/game_rules.py

from Config.imports import (BaseModel, ConfigDict, Field, Literal,
	field_validator, model_validator, re, UUID, datetime, Any)
from backend.app.Schemas.rule_calculations import (AttributeCalculations, StatFormula, validate_modifier_formula)


CheckKind = Literal["ability", "save", "attack"]

Degree = Literal[
	"critical_failure",
	"failure",
	"success",
	"critical_success",
]

class RulesModel(BaseModel):
	model_config = ConfigDict(
		extra="forbid",
		strict=True,
		validate_default=True,
	)

class ProficiencyRank(RulesModel):
	label: str = Field(min_length=1, max_length=100)

	# Индекс 0 соответствует первому уровню.
	# Таблица позволяет настраивать прогрессию без выполнения кода.
	bonuses: list[int] = Field(min_length=1, max_length=100)

	contexts: list[CheckKind] = Field(
		default_factory=lambda: ["ability", "save", "attack"],
		min_length=1,
		max_length=3,
	)

	@field_validator("bonuses")
	@classmethod
	def validate_bonuses(cls, values):
		if any(abs(value) > 1000 for value in values):
			raise ValueError("Бонус владения выходит за допустимый диапазон")
		return values

	@field_validator("contexts")
	@classmethod
	def validate_contexts(cls, values):
		if len(values) != len(set(values)):
			raise ValueError("Виды проверок не должны повторяться")
		return values

class NaturalRollRule(RulesModel):
	on_20: Literal[
		"ignore", "success", "critical_success", "improve",
	] = "ignore"

	on_1: Literal[
		"ignore", "failure", "critical_failure", "worsen",
	] = "ignore"

class CheckRules(RulesModel):
	degrees: Literal["binary", "four"] = "binary"
	critical_margin: int = Field(default=10, ge=1, le=1000)
	supports_advantage: bool = False

	natural: dict[CheckKind, NaturalRollRule]

	@model_validator(mode="after")
	def validate_natural_rules(self):
		required = {"ability", "save", "attack"}

		if set(self.natural) != required:
			raise ValueError(
				"Нужны правила натуральных бросков "
				"для ability, save и attack"
			)

		if self.degrees == "binary":
			for rule in self.natural.values():
				if rule.on_20 == "improve" or rule.on_1 == "worsen":
					raise ValueError(
						"Сдвиг степени результата требует "
						"четырёх степеней успеха"
					)

		return self

class RulesProfile(RulesModel):
	schema_version: Literal[1, 2] = 1

	# Это происхождение конфигурации, а не выбор класса по URL.
	base_ruleset: Literal[
		"dnd5e_2014_srd51",
		"pf2e_remaster",
	]

	# В D&D хранится значение характеристики.
	# В PF2e Remaster используется непосредственно модификатор.
	attribute_mode: Literal["score", "modifier"]

	attribute_codes: list[str] = Field(
		min_length=1,
		max_length=40,
	)

	modifier_offset: int = Field(default=10, ge=-1000, le=1000)
	modifier_divisor: int = Field(default=2, ge=1, le=1000)
	# None — использовать прежнее правило offset/divisor.
	modifier_formula: StatFormula | None = None


	max_level: int = Field(default=20, ge=1, le=100)

	proficiency_ranks: dict[str, ProficiencyRank] = Field(
		min_length=1,
		max_length=32,
	)

	checks: CheckRules

	calculations: AttributeCalculations | None = None

	@model_validator(mode="after")
	def validate_calculations(self):
		validate_modifier_formula(self.modifier_formula)

		if self.schema_version == 1:
			if self.calculations is not None:
				raise ValueError(
					"Настраиваемые вычисления требуют "
					"schema_version=2"
				)

			if self.modifier_formula is not None:
				raise ValueError(
					"Собственная формула модификатора требует "
					"schema_version=2"
				)

			return self

		if self.calculations is None:
			raise ValueError(
				"Для schema_version=2 требуется раздел calculations"
			)

		if set(self.calculations.attributes) != set(self.attribute_codes):
			raise ValueError(
				"Определения характеристик должны точно "
				"соответствовать attribute_codes"
			)

		return self

	@field_validator("attribute_codes")
	@classmethod
	def validate_attribute_codes(cls, values):
		if len(values) != len(set(values)):
			raise ValueError("Коды характеристик должны быть уникальными")

		for value in values:
			if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", value):
				raise ValueError("Недопустимый код характеристики")

		return values

	@model_validator(mode="after")
	def validate_proficiency_tables(self):
		for code, rank in self.proficiency_ranks.items():
			if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", code):
				raise ValueError("Недопустимый код ранга владения")

			if len(rank.bonuses) != self.max_level:
				raise ValueError(
					f"Ранг {code}: необходимо указать бонус "
					f"для каждого из {self.max_level} уровней"
				)

		return self

class CheckInput(RulesModel):
	kind: CheckKind
	level: int = Field(ge=1, le=100)
	attribute_code: str = Field(min_length=1, max_length=40)

	# Уже полученное значение характеристики:
	# score для D&D, modifier для PF2e Remaster.
	attribute_value: int = Field(ge=-1000, le=1000)

	proficiency_rank: str = Field(min_length=1, max_length=40)

	# Уже разрешённая сумма дополнительных бонусов и штрафов.
	# Совместимость эффектов здесь пока не вычисляется.
	resolved_bonus: int = Field(default=0, ge=-10000, le=10000)

	dc: int = Field(ge=-10000, le=10000)

	# Проверочный API принимает готовые результаты костей.
	# Он не создаёт настоящие игровые броски.
	dice: list[int] = Field(min_length=1, max_length=2)

	advantage: bool = False
	disadvantage: bool = False

	@field_validator("dice")
	@classmethod
	def validate_dice(cls, values):
		if any(value < 1 or value > 20 for value in values):
			raise ValueError("Результат d20 должен быть от 1 до 20")
		return values

class CheckResult(RulesModel):
	die: int
	attribute_modifier: int
	proficiency_bonus: int
	resolved_bonus: int
	total: int
	dc: int

	degree_before_natural: Degree
	degree: Degree

class CheckPreviewInput(RulesModel):
	rules: RulesProfile
	check: CheckInput

class AttributePreviewInput(RulesModel):
	rules: RulesProfile
	level: int = Field(ge=1, le=100)

	attributes: dict[str, int] = Field(
		min_length=1,
		max_length=40,
	)

class GameSystemRulesDraftCreate(RulesModel):
	rules: RulesProfile

class GameSystemRulesDraftUpdate(RulesModel):
	expected_revision: int = Field(ge=1)
	rules: RulesProfile

class GameSystemRulesPublish(RulesModel):
	expected_revision: int = Field(ge=1)

class GameRulesVersionBind(RulesModel):
	rules_version_id: UUID

	# Обязательное поле запроса.
	# null означает, что клиент ожидает отсутствие закреплённой версии.
	expected_rules_version_id: UUID | None = Field(...)

class GameSystemRulesDraftRead(RulesModel):
	model_config = ConfigDict(
		from_attributes=True,
		populate_by_name=True,
	)
	engine_version_id: UUID | None = None

	rules_overrides: dict[str, Any] | None = Field(
		default=None,
		validation_alias="rules_overrides_json",
	)
	id: UUID
	system_id: UUID
	revision: int

	rules: RulesProfile = Field(validation_alias="rules_json")

	created_at: datetime
	updated_at: datetime

class GameSystemRulesDraftState(RulesModel):
	draft: GameSystemRulesDraftRead | None

class GameSystemRulesVersionRead(RulesModel):
	model_config = ConfigDict(
		from_attributes=True,
		populate_by_name=True,
	)

	engine_version_id: UUID | None = None

	rules_overrides: dict[str, Any] | None = Field(
		default=None,
		validation_alias="rules_overrides_json",
	)

	id: UUID
	system_id: UUID
	version_number: int

	rules: RulesProfile = Field(validation_alias="rules_json")

	rules_engine_version: str
	published_at: datetime

class GameSystemRulesPublishedState(RulesModel):
	version: GameSystemRulesVersionRead | None