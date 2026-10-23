# backend/app/Routers/lobby.py

from Config.imports import (APIRouter, Depends, status, AsyncSession, UUID,
                            Request, HTMLResponse, CsrfProtect, HTTPException, JSONResponse)
from backend.app.Database.database import get_async_session
from backend.app.Core.csrf import enforce_csrf
from backend.app.Services.Core.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Schemas.lobby import (GameCreate, GameUpdate, GameRead,
                                       PartyRead, PartyRoleUpdate, InviteCreate, InviteRead, InviteClaim,
                                       SessionCreate, SessionUpdate, SessionRead)
from backend.app.Services.Games import lobby_service as svc, game_deletion_service

router = APIRouter(
	prefix="/games",
	tags=["lobby"]
)

@router.get("", response_class=HTMLResponse, name="games_page_get")
async def get_games_page(request: Request, user: User = Depends(get_current_user), csrf_protect: CsrfProtect = Depends()):
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {
		"user": user,
		"csrf_token": csrf_token,
	}
	templates = request.app.state.templates
	response = templates.TemplateResponse(request, "games/games.html", context)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.get("/list", response_model=list[GameRead], operation_id="listGames")
async def list_games(session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.list_games_for_user(session, current_user.id)

@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED,
             operation_id="createGame", dependencies=[Depends(enforce_csrf)])
async def create_game(data: GameCreate, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.create_game(session, current_user.id, data)

@router.get("/{game_id}/details", response_class=HTMLResponse, name="game_details_page_get", operation_id="getGameDetailsPage")
async def get_game_details_page(request: Request, game_id: UUID, session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user), csrf_protect: CsrfProtect = Depends()):
	# Мастер либо активный незаблокированный участник.
	game = await svc.get_game(session, game_id, user.id)

	csrf_token, signed_token = (csrf_protect.generate_csrf_tokens())

	context = {
		"user": user,
		"csrf_token": csrf_token,
		"game": game,
		"is_game_master": game.master_id == user.id,
	}

	response = request.app.state.templates.TemplateResponse(
		request,
		"games/game_details.html",
		context,
	)

	csrf_protect.set_csrf_cookie(
		signed_token,
		response,
	)
	return response

@router.get("/{game_id}", response_model=GameRead, operation_id="getGame")
async def get_game(game_id: UUID, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.get_game(session, game_id, current_user.id)

@router.patch("/{game_id}", response_model=GameRead, operation_id="updateGame",
              dependencies=[Depends(enforce_csrf)])
async def update_game(game_id: UUID, data: GameUpdate, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.update_game(session, game_id, current_user.id, data)

@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="archiveGame",
               dependencies=[Depends(enforce_csrf)])
async def archive_game(game_id: UUID, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	await svc.archive_game(session, game_id, current_user.id)

@router.get("/{game_id}/party", response_model=list[PartyRead], operation_id="listParty")
async def list_party(game_id: UUID, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.list_party(session, game_id, current_user.id)

@router.patch("/{game_id}/party/{user_id}", response_model=PartyRead, operation_id="updatePartyRole",
              dependencies=[Depends(enforce_csrf)])
async def update_party_role(game_id: UUID, user_id: UUID, data: PartyRoleUpdate,
		session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.update_party_role(session, game_id, user_id, current_user.id, data.role_in_game)

@router.post("/{game_id}/leave", status_code=status.HTTP_204_NO_CONTENT, operation_id="leaveGame",
             dependencies=[Depends(enforce_csrf)])
async def leave_game(game_id: UUID, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	await svc.leave_game(session, game_id, current_user.id)

@router.post("/{game_id}/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED,
             operation_id="createInvite", dependencies=[Depends(enforce_csrf)])
async def create_invite(game_id: UUID, data: InviteCreate, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.create_invite(session, game_id, current_user.id, data)

@router.post("/invites/claim", response_model=PartyRead, operation_id="claimInvite",
             dependencies=[Depends(enforce_csrf)])
async def claim_invite(data: InviteClaim, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.claim_invite(session, data.token, current_user.id)

# --- Sessions ---

@router.post("/{game_id}/sessions", response_model=SessionRead, status_code=status.HTTP_201_CREATED,
             operation_id="startSession", dependencies=[Depends(enforce_csrf)])
async def start_session(game_id: UUID, data: SessionCreate, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.start_session(session, game_id, current_user.id, data)

@router.get("/{game_id}/sessions", response_model=list[SessionRead], operation_id="listSessions")
async def list_sessions(game_id: UUID, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.list_sessions(session, game_id, current_user.id)

@router.get("/{game_id}/sessions/active", response_model=SessionRead, operation_id="getActiveSession")
async def get_active_session(game_id: UUID, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.get_active_session(session, game_id, current_user.id)

@router.patch("/{game_id}/sessions/{session_id}", response_model=SessionRead, operation_id="updateSession",
              dependencies=[Depends(enforce_csrf)])
async def update_session(game_id: UUID, session_id: UUID, data: SessionUpdate,
		session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.update_session(session, session_id, current_user.id, data)

@router.post("/{game_id}/sessions/{session_id}/end", response_model=SessionRead, operation_id="endSession",
             dependencies=[Depends(enforce_csrf)])
async def end_session(game_id: UUID, session_id: UUID, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await svc.end_session(session, session_id, current_user.id)

# GET /games/{game_id}/play
@router.get("/{game_id}/play", response_class=HTMLResponse, name="game_play_page_get", operation_id="getGamePlayPage")
async def get_game_play_page(request: Request, game_id: UUID, session_id: UUID | None = None,
		session: AsyncSession = Depends(get_async_session), user: User = Depends(get_current_user),
		csrf_protect: CsrfProtect = Depends()):
	# Сервис проверяет доступ пользователя к игре.
	game_sessions = await svc.list_sessions(session, game_id, user.id)

	if session_id is not None:
		selected_session = next(
			(item for item in game_sessions if item.id == session_id),
			None,
		)
		if selected_session is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Сессия этой игры не найдена",
			)
	else:
		selected_session = next(
			(item for item in game_sessions if item.is_active),
			None,
		)

	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {
		"user": user,
		"csrf_token": csrf_token,
		"game_id": game_id,
		"game_sessions": game_sessions,
		"selected_session": selected_session,
		"session_id": selected_session.id if selected_session else None,
	}

	templates = request.app.state.templates
	response = templates.TemplateResponse(
		request,
		"games/game_play.html",
		context,
	)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.delete("/{game_id}/permanent", name="delete_game_permanently", operation_id="deleteGamePermanently",dependencies=[Depends(enforce_csrf)])
async def delete_game_permanently(game_id: UUID,session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	result = await game_deletion_service.delete_game(
		session,
		game_id,
		current_user.id,
	)

	return JSONResponse(
		status_code=(
			status.HTTP_200_OK
			if result["cleanup_complete"]
			else status.HTTP_202_ACCEPTED
		),
		content=result,
	)