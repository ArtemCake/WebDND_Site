# backend/app/Services/dice_service.py

import re

from Config.imports import (UUID, HTTPException, status, select, AsyncSession, secrets)
from backend.app.Database.Models.Gameplay.lobby import DiceRoll
from backend.app.Schemas.lobby import DiceRollIn


_FORMULA_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")

def _parse_formula(formula: str) -> tuple[int, int, int]:
	match = _FORMULA_RE.fullmatch(formula.strip().lower())
	if match is None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "Формула броска должна быть вида «2d6+3»")
	count, sides, modifier = match.groups()
	return int(count), int(sides), int(modifier) if modifier else 0

async def roll_dice(
		session: AsyncSession, session_id: UUID, roller_id: UUID, party_id: UUID | None, data: DiceRollIn,
) -> DiceRoll:
	count, sides, modifier = _parse_formula(data.formula)

	if data.advantage is not None and (count, sides) != (1, 20):
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "Преимущество/помеха поддерживаются только для броска 1d20")

	if data.advantage is not None:
		roll_a, roll_b = secrets.randbelow(sides) + 1, secrets.randbelow(sides) + 1
		individual = [roll_a, roll_b]
		chosen = max(roll_a, roll_b) if data.advantage == "advantage" else min(roll_a, roll_b)
		total = chosen + modifier
	else:
		individual = [secrets.randbelow(sides) + 1 for _ in range(count)]
		total = sum(individual) + modifier

	dice_roll = DiceRoll(
		session_id=session_id,
		roller_id=roller_id,
		party_id=party_id,
		formula=data.formula,
		result_total=total,
		individual_results=individual,
		advantage=data.advantage,
		is_gm_hidden=data.is_gm_hidden,
		context_type=data.context_type,
		context_target_id=data.context_target_id,
	)
	session.add(dice_roll)
	await session.commit()
	await session.refresh(dice_roll)
	return dice_roll

async def list_session_rolls(session: AsyncSession, session_id: UUID, viewer_is_master: bool) -> list[DiceRoll]:
	stmt = select(DiceRoll).where(DiceRoll.session_id == session_id).order_by(DiceRoll.created_at.desc())
	if not viewer_is_master:
		stmt = stmt.where(DiceRoll.is_gm_hidden.is_(False))
	return list((await session.execute(stmt)).scalars().all())