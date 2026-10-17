# backend/app/Services/lobby_service.py

from Config.imports import (AsyncSession, HTTPException, status, secrets, UUID, select)
from backend.app.Database.Models.Gameplay.lobby import Game, Party, Invite
from backend.app.Schemas.lobby import GameCreate, GameUpdate, InviteCreate


async def list_games_for_user(session: AsyncSession, user_id: UUID) -> list[Game]:
	result = await session.execute(
		select(Game)
		.join(Party, Party.game_id == Game.id)
		.where(Party.user_id == user_id, Party.is_active.is_(True))
	)
	return list(result.scalars().all())

async def create_game(session: AsyncSession, master_id: UUID, data: GameCreate) -> Game:
	game = Game(master_id=master_id, status="draft", **data.model_dump())
	session.add(game)
	await session.flush()

	session.add(Party(game_id=game.id, user_id=master_id, role_in_game="assistant_dm", is_active=True))
	await session.commit()
	await session.refresh(game)
	return game

async def _get_game_or_404(session: AsyncSession, game_id: UUID) -> Game:
	game = await session.get(Game, game_id)
	if game is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Игра не найдена")
	return game

async def _require_master(session: AsyncSession, game_id: UUID, user_id: UUID) -> Game:
	game = await _get_game_or_404(session, game_id)
	if game.master_id != user_id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только мастер игры может это делать")
	return game

async def get_game(session: AsyncSession, game_id: UUID, user_id: UUID) -> Game:
	game = await _get_game_or_404(session, game_id)
	member = await session.execute(
		select(Party).where(Party.game_id == game_id, Party.user_id == user_id)
	)
	if member.scalar_one_or_none() is None and game.master_id != user_id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой игре")
	return game

async def update_game(session: AsyncSession, game_id: UUID, master_id: UUID, data: GameUpdate) -> Game:
	game = await _require_master(session, game_id, master_id)
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(game, field, value)
	await session.commit()
	await session.refresh(game)
	return game

async def archive_game(session: AsyncSession, game_id: UUID, master_id: UUID) -> None:
	game = await _require_master(session, game_id, master_id)
	game.status = "archived"
	await session.commit()

async def list_party(session: AsyncSession, game_id: UUID, user_id: UUID) -> list[Party]:
	await get_game(session, game_id, user_id)  # проверка доступа
	result = await session.execute(select(Party).where(Party.game_id == game_id))
	return list(result.scalars().all())

async def update_party_role(
		session: AsyncSession, game_id: UUID, target_user_id: UUID, master_id: UUID, role_in_game: str
) -> Party:
	await _require_master(session, game_id, master_id)
	member = await session.execute(
		select(Party).where(Party.game_id == game_id, Party.user_id == target_user_id)
	)
	party = member.scalar_one_or_none()
	if party is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник не найден в этой игре")
	party.role_in_game = role_in_game
	await session.commit()
	await session.refresh(party)
	return party

async def leave_game(session: AsyncSession, game_id: UUID, user_id: UUID) -> None:
	member = await session.execute(
		select(Party).where(Party.game_id == game_id, Party.user_id == user_id)
	)
	party = member.scalar_one_or_none()
	if party is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вы не состоите в этой игре")
	party.is_active = False
	await session.commit()

async def create_invite(session: AsyncSession, game_id: UUID, master_id: UUID, data: InviteCreate) -> Invite:
	await _require_master(session, game_id, master_id)
	invite = Invite(
		token=secrets.token_urlsafe(24),
		game_id=game_id,
		creator_id=master_id,
		uses_current=0,
		**data.model_dump(),
	)
	session.add(invite)
	await session.commit()
	await session.refresh(invite)
	return invite

async def claim_invite(session: AsyncSession, token: str, user_id: UUID) -> Party:
	invite = await session.get(Invite, token)
	if invite is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
	if invite.is_expired:
		raise HTTPException(status_code=status.HTTP_410_GONE, detail="Приглашение больше не действует")

	existing = await session.execute(
		select(Party).where(Party.game_id == invite.game_id, Party.user_id == user_id)
	)
	party = existing.scalar_one_or_none()
	if party is not None:
		party.is_active = True
	else:
		party = Party(game_id=invite.game_id, user_id=user_id, role_in_game="player", is_active=True)
		session.add(party)

	invite.consume()
	invite.claimed_by = user_id
	await session.commit()
	await session.refresh(party)
	return party