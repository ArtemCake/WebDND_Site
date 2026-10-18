# backend/app/Services/token_service.py

from Config.imports import (UUID, HTTPException, status, select, AsyncSession)
from backend.app.Database.Models.Gameplay.maps import Token, MapHex
from backend.app.Database.Models.Gameplay.lobby import Session as GameSession
from backend.app.Services.lobby_service import is_game_master
from backend.app.Schemas.maps import TokenCreate, TokenUpdate, TokenMove


async def _get_token_or_404(session: AsyncSession, token_id: UUID) -> Token:
	token = await session.get(Token, token_id)
	if token is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Токен не найден")
	return token

async def _can_control_token(session: AsyncSession, token: Token, user_id: UUID, game_session: GameSession) -> bool:
	if token.owner_id == user_id:
		return True
	if token.controlled_by_ids and user_id in token.controlled_by_ids:
		return True
	return await is_game_master(session, game_session.game_id, user_id)

async def create_token(session: AsyncSession, master_id: UUID, data: TokenCreate) -> Token:
	game_session = await session.get(GameSession, data.session_id)
	if game_session is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Игровая сессия не найдена")
	if not await is_game_master(session, game_session.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может создавать токены")

	token = Token(owner_id=master_id, **data.model_dump())
	session.add(token)
	await session.commit()
	await session.refresh(token)
	return token

async def move_token(session: AsyncSession, token_id: UUID, mover_id: UUID, data: TokenMove) -> Token:
	token = await _get_token_or_404(session, token_id)
	game_session = await session.get(GameSession, token.session_id)
	if not await _can_control_token(session, token, mover_id, game_session):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не можете перемещать этот токен")

	if data.hex_id is not None:
		target_hex = await session.get(MapHex, data.hex_id)
		if target_hex is None:
			raise HTTPException(status.HTTP_404_NOT_FOUND, "Указанный гекс не найден")
		token.current_hex_id = target_hex.id

	token.grid_x = data.grid_x
	token.grid_y = data.grid_y
	await session.commit()
	await session.refresh(token)
	return token

async def update_token(session: AsyncSession, token_id: UUID, master_id: UUID, data: TokenUpdate) -> Token:
	token = await _get_token_or_404(session, token_id)
	game_session = await session.get(GameSession, token.session_id)
	if not await is_game_master(session, game_session.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может редактировать свойства токена")
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(token, field, value)
	await session.commit()
	await session.refresh(token)
	return token

async def delete_token(session: AsyncSession, token_id: UUID, master_id: UUID) -> None:
	token = await _get_token_or_404(session, token_id)
	game_session = await session.get(GameSession, token.session_id)
	if not await is_game_master(session, game_session.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может удалять токены")
	await session.delete(token)
	await session.commit()

async def list_tokens_for_session(session: AsyncSession, session_id: UUID) -> list[Token]:
	result = await session.execute(select(Token).where(Token.session_id == session_id))
	return list(result.scalars().all())