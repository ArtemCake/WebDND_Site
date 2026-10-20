# backend/app/Routers/maps.py

from Config.imports import (APIRouter, Depends, UUID, AsyncSession, Request, HTMLResponse, CsrfProtect)
from backend.app.Database.database import get_async_session
from backend.app.Core.csrf import enforce_csrf
from backend.app.Services.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Services import lobby_service
from backend.app.Schemas.maps import (MapCreate, MapUpdate, MapRead,
	HexGridGenerateIn, MapLayerRead, FogOfWarRecalcIn, FogOfWarRecalcOut)
from backend.app.Services import map_hex_service as svc


router = APIRouter(
	prefix="/maps",
	tags=["maps"]
)

# --- Campaign maps ---

@router.get("", response_class=HTMLResponse, name="maps_page_get", operation_id="getMapsPage")
async def get_maps_page(request: Request, game_id: UUID | None = None,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user),
		csrf_protect: CsrfProtect = Depends(),
):
	games = await lobby_service.list_games_for_user(
		session,
		user.id,
	)

	selected_game = None
	campaign_maps = []
	can_manage_maps = False

	if game_id is not None:
		selected_game = await lobby_service.get_game(
			session,
			game_id,
			user.id,
		)

		can_manage_maps = selected_game.master_id == user.id

		# Не раскрываем игроку весь каталог карт кампании.
		# Правила показа карт игрокам подключим отдельно.
		if can_manage_maps:
			campaign_maps = await svc.list_maps_for_game(
				session,
				selected_game.id,
			)

	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

	context = {
		"user": user,
		"csrf_token": csrf_token,
		"games": games,
		"selected_game": selected_game,
		"campaign_maps": campaign_maps,
		"can_manage_maps": can_manage_maps,
	}

	templates = request.app.state.templates
	response = templates.TemplateResponse(
		request,
		"maps.html",
		context,
	)

	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.post("", response_model=MapRead, operation_id="createMap", dependencies=[Depends(enforce_csrf)])
async def create_map(data: MapCreate, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.create_map(session, current_user.id, data)

# GET /maps/by-game/{game_id}
@router.get("/by-game/{game_id}", response_model=list[MapRead], operation_id="listMapsForGame")
async def list_maps_for_game(
		game_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.list_maps_for_game(session, game_id)

@router.get("/{map_id}", response_model=MapRead, operation_id="getMap")
async def get_map(
		map_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.get_map(session, map_id)

@router.patch("/{map_id}", response_model=MapRead, operation_id="updateMap", dependencies=[Depends(enforce_csrf)])
async def update_map(
		map_id: UUID,
		data: MapUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_map(session, map_id, current_user.id, data)

@router.post("/{map_id}/activate", response_model=MapRead, operation_id="activateMap", dependencies=[Depends(enforce_csrf)])
async def activate_map(
		map_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.set_active_map(session, map_id, current_user.id)

@router.delete("/{map_id}", status_code=204, operation_id="deleteMap", dependencies=[Depends(enforce_csrf)])
async def delete_map(
		map_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await svc.delete_map(session, map_id, current_user.id)

# --- Hex grid & fog of war ---

# POST /maps/{map_id}/hex-grid
@router.post("/{map_id}/hex-grid", response_model=MapLayerRead, operation_id="generateHexGrid",
             dependencies=[Depends(enforce_csrf)])
async def generate_hex_grid(
		map_id: UUID,
		payload: HexGridGenerateIn,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.generate_hex_grid(session, map_id, current_user.id, payload.rows, payload.cols)

# POST /maps/{map_id}/fog-of-war/recalc
@router.post("/{map_id}/fog-of-war/recalc", response_model=FogOfWarRecalcOut, operation_id="recalcFogOfWar",
             dependencies=[Depends(enforce_csrf)])
async def recalc_fog_of_war(
		map_id: UUID,
		payload: FogOfWarRecalcIn,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	visible_ids = await svc.recalc_fog_of_war(session, map_id, payload.viewer_token_ids)
	return FogOfWarRecalcOut(visible_hex_ids=list(visible_ids))