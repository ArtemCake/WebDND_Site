# backend/app/Services/GameSystems/rules_engine.py

from backend.app.Schemas.game_rules import (RulesProfile, CheckInput, CheckResult)


_DEGREES = (
	"critical_failure",
	"failure",
	"success",
	"critical_success",
)

def calculate_attribute_modifier(rules: RulesProfile, value: int) -> int:
	if rules.attribute_mode == "modifier":
		return value

	return (
			(value - rules.modifier_offset)
			// rules.modifier_divisor
	)

def calculate_proficiency(rules: RulesProfile, level: int, rank_code: str, kind: str) -> int:
	if level < 1 or level > rules.max_level:
		raise ValueError(
			f"Уровень должен быть от 1 до {rules.max_level}"
		)

	rank = rules.proficiency_ranks.get(rank_code)

	if rank is None:
		raise ValueError("Неизвестный ранг владения")

	if kind not in rank.contexts:
		raise ValueError(
			"Этот ранг владения не применяется "
			"к выбранному виду проверки"
		)

	return rank.bonuses[level - 1]

def _select_die(rules: RulesProfile, check: CheckInput) -> int:
	has_advantage_flags = check.advantage or check.disadvantage

	if has_advantage_flags and not rules.checks.supports_advantage:
		raise ValueError(
			"Этот набор правил не поддерживает "
			"механику преимущества и помехи"
		)

	# В D&D преимущество и помеха взаимно отменяются.
	use_two = check.advantage != check.disadvantage
	required_count = 2 if use_two else 1

	if len(check.dice) != required_count:
		raise ValueError(
			f"Для этой проверки нужно результатов d20: "
			f"{required_count}"
		)

	if not use_two:
		return check.dice[0]

	if check.advantage:
		return max(check.dice)

	return min(check.dice)

def _base_degree(rules: RulesProfile, total: int, dc: int) -> int:
	if rules.checks.degrees == "binary":
		return 2 if total >= dc else 1

	margin = rules.checks.critical_margin

	if total >= dc + margin:
		return 3

	if total >= dc:
		return 2

	if total <= dc - margin:
		return 0

	return 1

def _apply_natural(rules: RulesProfile, check: CheckInput, die: int, degree: int) -> int:
	natural = rules.checks.natural[check.kind]

	if die == 20:
		if natural.on_20 == "improve":
			return min(3, degree + 1)

		if natural.on_20 == "success":
			return 2

		if natural.on_20 == "critical_success":
			return 3

	if die == 1:
		if natural.on_1 == "worsen":
			return max(0, degree - 1)

		if natural.on_1 == "failure":
			return 1

		if natural.on_1 == "critical_failure":
			return 0

	return degree

def evaluate_check(rules: RulesProfile, check: CheckInput) -> CheckResult:
	if check.attribute_code not in rules.attribute_codes:
		raise ValueError(
			"Характеристика отсутствует в выбранном наборе правил"
		)

	die = _select_die(rules, check)

	attribute_modifier = calculate_attribute_modifier(
		rules, check.attribute_value,
	)

	proficiency_bonus = calculate_proficiency(
		rules,
		check.level,
		check.proficiency_rank,
		check.kind,
	)

	total = (
			die
			+ attribute_modifier
			+ proficiency_bonus
			+ check.resolved_bonus
	)

	before_natural = _base_degree(rules, total, check.dc)

	degree = _apply_natural(
		rules, check, die, before_natural,
	)

	return CheckResult(
		die=die,
		attribute_modifier=attribute_modifier,
		proficiency_bonus=proficiency_bonus,
		resolved_bonus=check.resolved_bonus,
		total=total,
		dc=check.dc,
		degree_before_natural=_DEGREES[before_natural],
		degree=_DEGREES[degree],
	)