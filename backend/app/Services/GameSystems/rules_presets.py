# backend/app/Services/GameSystems/rules_presets.py

from backend.app.Schemas.game_rules import (RulesProfile, ProficiencyRank, CheckRules, NaturalRollRule)


def _dnd5e_2014() -> RulesProfile:
	proficiency = [
		2 + (level - 1) // 4
		for level in range(1, 21)
	]

	return RulesProfile(
		base_ruleset="dnd5e_2014_srd51",
		attribute_mode="score",
		attribute_codes=["str", "dex", "con", "int", "wis", "cha"],
		max_level=20,
		proficiency_ranks={
			"none": ProficiencyRank(
				label="Нет владения",
				bonuses=[0] * 20,
			),
			"proficient": ProficiencyRank(
				label="Владение",
				bonuses=proficiency,
			),
			"expertise": ProficiencyRank(
				label="Удвоенный бонус мастерства",
				bonuses=[value * 2 for value in proficiency],
				contexts=["ability"],
			),
			"half": ProficiencyRank(
				label="Половина бонуса мастерства",
				bonuses=[value // 2 for value in proficiency],
				contexts=["ability"],
			),
		},
		checks=CheckRules(
			degrees="binary",
			supports_advantage=True,
			natural={
				"ability": NaturalRollRule(),
				"save": NaturalRollRule(),
				"attack": NaturalRollRule(
					on_20="critical_success",
					on_1="failure",
				),
			},
		),
	)

def _pf2e_remaster() -> RulesProfile:
	ranks = {
		"untrained": ProficiencyRank(
			label="Нет подготовки",
			bonuses=[0] * 20,
		),
	}

	for code, label, base in (
			("trained", "Обученный", 2),
			("expert", "Эксперт", 4),
			("master", "Мастер", 6),
			("legendary", "Легенда", 8),
	):
		ranks[code] = ProficiencyRank(
			label=label,
			bonuses=[
				level + base
				for level in range(1, 21)
			],
		)

	return RulesProfile(
		base_ruleset="pf2e_remaster",
		attribute_mode="modifier",
		attribute_codes=["str", "dex", "con", "int", "wis", "cha"],
		max_level=20,
		proficiency_ranks=ranks,
		checks=CheckRules(
			degrees="four",
			critical_margin=10,
			supports_advantage=False,
			natural={
				kind: NaturalRollRule(
					on_20="improve",
					on_1="worsen",
				)
				for kind in ("ability", "save", "attack")
			},
		),
	)

def get_rules_preset(code: str) -> RulesProfile:
	# Каждый вызов создаёт независимый набор настроек.
	if code == "dnd5e_2014_srd51":
		return _dnd5e_2014()

	if code == "pf2e_remaster":
		return _pf2e_remaster()

	raise ValueError("Неизвестный исходный набор правил")

def list_rules_presets() -> list[dict]:
	return [
		{
			"code": "dnd5e_2014_srd51",
			"name": "D&D 5e 2014 — SRD 5.1",
			"rules": _dnd5e_2014().model_dump(mode="json"),
		},
		{
			"code": "pf2e_remaster",
			"name": "Pathfinder 2e Remaster",
			"rules": _pf2e_remaster().model_dump(mode="json"),
		},
	]