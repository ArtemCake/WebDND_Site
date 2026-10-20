# backend/app/Services/dice_service.py

import re

from Config.imports import (UUID, HTTPException, status, select, AsyncSession, secrets)
from backend.app.Database.Models.Gameplay.lobby import DiceRoll, Party
from backend.app.Services.lobby_service import (get_session_for_user, is_game_master)
from backend.app.Schemas.lobby import DiceRollIn


_FORMULA_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")

def _parse_formula(formula: str) -> tuple[int, int, int]:
	match = _FORMULA_RE.fullmatch(formula.strip().lower())

	if match is None:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Формула броска должна быть вида «2d6+3»",
		)

	count_text, sides_text, modifier_text = match.groups()
	count = int(count_text)
	sides = int(sides_text)
	modifier = int(modifier_text) if modifier_text else 0

	if count < 1:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Количество костей должно быть не меньше 1",
		)

	if sides < 1:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Количество граней должно быть не меньше 1",
		)

	return count, sides, modifier

async def roll_dice(
		session: AsyncSession, session_id: UUID, roller_id: UUID, party_id: UUID | None, data: DiceRollIn,
) -> DiceRoll:

	game_session = await get_session_for_user(
		session,
		session_id,
		roller_id,
		require_active=True,
	)

	roller_is_master = await is_game_master(
		session,
		game_session.game_id,
		roller_id,
	)

	if data.is_gm_hidden and not roller_is_master:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Только мастер игры может выполнять скрытые броски",
		)

	if party_id is not None:
		party = await session.get(Party, party_id)

		if party is None or party.game_id != game_session.game_id:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Участник не принадлежит игре этой сессии",
			)

		if not party.is_active or party.role_in_game == "banned":
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail="Участник не имеет активного доступа к игре",
			)

		if party.user_id != roller_id and not roller_is_master:
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail="Нельзя привязать бросок к другому участнику",
			)

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

async def list_session_rolls(session: AsyncSession, session_id: UUID, viewer_id: UUID) -> list[DiceRoll]:
	game_session = await get_session_for_user(
		session,
		session_id,
		viewer_id,
	)

	viewer_is_master = await is_game_master(
		session,
		game_session.game_id,
		viewer_id,
	)

	stmt = (
		select(DiceRoll)
		.where(DiceRoll.session_id == session_id)
		.order_by(DiceRoll.created_at.desc())
	)

	if not viewer_is_master:
		stmt = stmt.where(DiceRoll.is_gm_hidden.is_(False))

	result = await session.execute(stmt)
	return list(result.scalars().all())