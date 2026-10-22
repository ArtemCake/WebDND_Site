# backend/app/Services/Games/initiative_service.py

from Config.imports import (UUID, HTTPException, status, AsyncSession)
from backend.app.Database.Models.Gameplay.lobby import InitiativeTracker, Session as GameSession
from backend.app.Services.Games.lobby_service import is_game_master


async def _require_master_for_session(session: AsyncSession, session_id: UUID, master_id: UUID) -> GameSession:
	game_session = await session.get(GameSession, session_id)
	if game_session is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Игровая сессия не найдена")
	if not await is_game_master(session, game_session.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может управлять очередью ходов")
	return game_session

async def start_combat(session: AsyncSession, session_id: UUID, master_id: UUID, combatants: list[dict]) -> InitiativeTracker:
	await _require_master_for_session(session, session_id, master_id)
	if await session.get(InitiativeTracker, session_id) is not None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "Бой в этой сессии уже идёт")

	ordered = sorted(combatants, key=lambda c: c["initiative"], reverse=True)
	tracker = InitiativeTracker(session_id=session_id, turn_order_json=ordered, current_index=0, round_number=1)
	session.add(tracker)
	await session.commit()
	await session.refresh(tracker)
	return tracker

async def next_turn(session: AsyncSession, session_id: UUID, master_id: UUID) -> InitiativeTracker:
	await _require_master_for_session(session, session_id, master_id)
	tracker = await session.get(InitiativeTracker, session_id)
	if tracker is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Бой в этой сессии не начат")
	if not tracker.turn_order_json:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "Очередь ходов пуста")

	tracker.current_index += 1
	if tracker.current_index >= len(tracker.turn_order_json):
		tracker.current_index = 0
		tracker.round_number += 1
	await session.commit()
	await session.refresh(tracker)
	return tracker

async def end_combat(session: AsyncSession, session_id: UUID, master_id: UUID) -> None:
	await _require_master_for_session(session, session_id, master_id)
	tracker = await session.get(InitiativeTracker, session_id)
	if tracker is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Бой в этой сессии не начат")
	await session.delete(tracker)
	await session.commit()