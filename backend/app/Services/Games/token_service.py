# backend/app/Services/Games/token_service.py

from Config.imports import (UUID, HTTPException, status, select, AsyncSession)
from backend.app.Database.Models.Gameplay.lobby import Session as GameSession
from backend.app.Services.Games.lobby_service import (get_game, get_session_for_user, is_game_master)
from backend.app.Schemas.maps import TokenCreate, TokenUpdate, TokenMove
from backend.app.Database.Models.Gameplay.maps import (Token, MapHex, MapLayer, CampaignMap)


async def _get_token_or_404(session: AsyncSession, token_id: UUID) -> Token:
	token = (
		await session.execute(
			select(Token)
			.where(Token.id == token_id)
			.with_for_update(of=Token)
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()

	if token is None:
		raise HTTPException(
			status.HTTP_404_NOT_FOUND,
			"Токен не найден",
		)

	return token

async def _validate_token_map_for_session(session: AsyncSession, map_id: UUID | None, game_session: GameSession) -> None:
	if map_id is None:
		return

	campaign_map = (
		await session.execute(
			select(CampaignMap)
			.where(CampaignMap.id == map_id)
			.with_for_update()
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()

	if campaign_map is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Указанная карта не найдена",
		)

	if campaign_map.game_id != game_session.game_id:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Карта не принадлежит игре этой сессии",
		)

	if (
			campaign_map.session_id is not None
			and campaign_map.session_id != game_session.id
	):
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Карта привязана к другой игровой сессии",
		)

async def _can_control_token(session: AsyncSession, token: Token, user_id: UUID, game_session: GameSession | None) -> bool:
	if game_session is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Игровая сессия не найдена",
		)

	game = await get_game(
		session,
		game_session.game_id,
		user_id,
	)

	if game.master_id == user_id:
		return True

	if not token.is_visible_to_players:
		return False

	if token.owner_id == user_id:
		return True

	return (
			token.controlled_by_ids is not None
			and user_id in token.controlled_by_ids
	)

async def create_token(session: AsyncSession, master_id: UUID, data: TokenCreate) -> Token:
	game_session = await session.get(GameSession, data.session_id)

	if game_session is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Игровая сессия не найдена",
		)

	if not await is_game_master(
			session,
			game_session.game_id,
			master_id,
	):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Только мастер игры может создавать токены",
		)

	await _validate_token_map_for_session(
		session,
		data.current_map_id,
		game_session,
	)

	token = Token(
		owner_id=master_id,
		**data.model_dump(),
	)

	session.add(token)
	await session.commit()
	await session.refresh(token)
	return token

async def move_token(session: AsyncSession,	token_id: UUID,	mover_id: UUID,	data: TokenMove) -> Token:
	token = await _get_token_or_404(session, token_id)
	game_session = await session.get(GameSession, token.session_id)

	if not await _can_control_token(
			session,
			token,
			mover_id,
			game_session,
	):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Вы не можете перемещать этот токен",
		)
	await _validate_token_map_for_session(session, token.current_map_id, game_session)

	target_hex = None

	if data.hex_id is not None:
		if token.current_map_id is None:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=(
					"Перед перемещением на гекс "
					"необходимо назначить токену карту"
				),
			)

		target_hex = await session.get(MapHex, data.hex_id)

		if target_hex is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Указанный гекс не найден",
			)

		target_layer = await session.get(
			MapLayer,
			target_hex.layer_id,
		)

		if target_layer is None:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="Слой целевого гекса не найден",
			)

		if target_layer.map_id != token.current_map_id:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Целевой гекс не принадлежит текущей карте токена",
			)

	# Меняем положение только после успешного завершения проверок.
	if target_hex is not None:
		token.current_hex_id = target_hex.id

	token.grid_x = data.grid_x
	token.grid_y = data.grid_y
	await session.commit()
	await session.refresh(token)
	return token

async def update_token(session: AsyncSession, token_id: UUID, master_id: UUID, data: TokenUpdate) -> Token:
	token = await _get_token_or_404(session, token_id)
	game_session = await session.get(GameSession, token.session_id)

	if game_session is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Игровая сессия не найдена",
		)

	if not await is_game_master(
			session,
			game_session.game_id,
			master_id,
	):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=(
				"Только мастер игры может "
				"редактировать свойства токена"
			),
		)

	changes = data.model_dump(exclude_unset=True)
	reset_current_hex = False

	if "current_map_id" in changes:
		new_map_id = changes["current_map_id"]

		await _validate_token_map_for_session(
			session,
			new_map_id,
			game_session,
		)

		reset_current_hex = (
				new_map_id != token.current_map_id
				or new_map_id is None
		)

	# Изменяем объект только после проверки назначаемой карты.
	for field, value in changes.items():
		setattr(token, field, value)

	if reset_current_hex:
		token.current_hex_id = None

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

async def list_tokens_for_session(session: AsyncSession, session_id: UUID, viewer_id: UUID) -> list[Token]:
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

	stmt = select(Token).where(Token.session_id == session_id)

	if not viewer_is_master:
		stmt = stmt.where(Token.is_visible_to_players.is_(True))

	result = await session.execute(stmt)
	return list(result.scalars().all())