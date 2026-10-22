# backend/app/Services/Games/initiative_service.py

from Config.imports import (UUID, HTTPException, status, AsyncSession)
from backend.app.Database.Models.Gameplay.lobby import InitiativeTracker, Session as GameSession
from backend.app.Services.Games.lobby_service import (is_game_master, get_session_for_user)


async def _require_master_for_session(session: AsyncSession, session_id: UUID, master_id: UUID) -> GameSession:
	game_session = await session.get(GameSession, session_id)
	if game_session is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Игровая сессия не найдена")
	if not await is_game_master(session, game_session.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может управлять очередью ходов")
	return game_session

async def get_combat_state(session: AsyncSession, session_id: UUID, viewer_id: UUID) -> dict:
	"""Читает сохранённое состояние боя без изменения очереди."""
	game_session = await get_session_for_user(session, session_id, viewer_id)
	tracker = await session.get(InitiativeTracker, session_id)

	if tracker is None:
		return {
			"session_id": game_session.id,
			"session_active": game_session.is_active,
			"combat_active": False,
			"turn_order": [],
			"current_index": None,
			"round_number": None,
		}

	# Проверяем структуру сохранённого состояния.
	order = tracker.turn_order_json

	if (
			not isinstance(order, list)
			or any(not isinstance(item, dict) for item in order)
			or (
			order
			and not 0 <= tracker.current_index < len(order)
	)
	):
		raise HTTPException(
			status.HTTP_409_CONFLICT,
			"Сохранённая очередь боя некорректна",
		)

	# Для панели очереди нужны только имя и инициатива.
	# Не выдаём произвольное содержимое JSON, HP и внутренние ссылки.
	public_order = [
		{
			"name": item.get("name"),
			"initiative": item.get("initiative"),
		}
		for item in order
	]

	return {
		"session_id": game_session.id,
		"session_active": game_session.is_active,
		"combat_active": tracker.is_active,
		"turn_order": public_order,
		"current_index": (
			tracker.current_index if public_order else None
		),
		"round_number": tracker.round_number,
	}

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