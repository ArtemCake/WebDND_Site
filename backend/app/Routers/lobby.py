# backend/app/Routers/lobby.py

from Config.imports import (APIRouter, Depends, status, AsyncSession, UUID)
from backend.app.Database.database import get_async_session
from backend.app.Core.csrf import enforce_csrf
from backend.app.Services.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Schemas.lobby import (GameCreate, GameUpdate, GameRead,
	PartyRead, PartyRoleUpdate,	InviteCreate, InviteRead, InviteClaim)
from backend.app.Services import lobby_service as svc


router = APIRouter(
	prefix="/games",
	tags=["lobby"]
)

@router.get("", response_model=list[GameRead])
async def list_games(
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.list_games_for_user(session, current_user.id)


@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
async def create_game(
		data: GameCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.create_game(session, current_user.id, data)

@router.get("/{game_id}", response_model=GameRead)
async def get_game(
		game_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.get_game(session, game_id, current_user.id)

@router.patch("/{game_id}", response_model=GameRead, dependencies=[Depends(enforce_csrf)])
async def update_game(
		game_id: UUID,
		data: GameUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_game(session, game_id, current_user.id, data)

@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
async def archive_game(
		game_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await svc.archive_game(session, game_id, current_user.id)

@router.get("/{game_id}/party", response_model=list[PartyRead])
async def list_party(
		game_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.list_party(session, game_id, current_user.id)

@router.patch("/{game_id}/party/{user_id}", response_model=PartyRead,
              dependencies=[Depends(enforce_csrf)])
async def update_party_role(
		game_id: UUID,
		user_id: UUID,
		data: PartyRoleUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_party_role(session, game_id, user_id, current_user.id, data.role_in_game)

@router.post("/{game_id}/leave", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(enforce_csrf)])
async def leave_game(
		game_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await svc.leave_game(session, game_id, current_user.id)

@router.post("/{game_id}/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
async def create_invite(
		game_id: UUID,
		data: InviteCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.create_invite(session, game_id, current_user.id, data)

@router.post("/invites/claim", response_model=PartyRead, dependencies=[Depends(enforce_csrf)])
async def claim_invite(
		data: InviteClaim,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.claim_invite(session, data.token, current_user.id)