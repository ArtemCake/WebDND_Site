# backend/app/Routers/content.py

from Config.imports import (APIRouter, Depends, AsyncSession, UUID, HTTPException, status)
from backend.app.Database.database import get_async_session
from backend.app.Services.Core.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Schemas.content import GameSystemRead
from backend.app.Services import content_service as svc
from backend.app.Enums.enums_BD import SystemRole, AdminPermission


router = APIRouter(
	prefix="/game-systems",
	tags=["content"],
)

@router.get("", response_model=list[GameSystemRead], operation_id="listGameSystems")
async def list_game_systems(session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.list_active_systems(session)

@router.get("/access", operation_id="getGameSystemsCatalogAccess")
async def game_systems_catalog_access(current_user: User = Depends(get_current_user)):
	can_manage = (
			SystemRole.ADMIN in (current_user.roles or [])
			and AdminPermission.CONTENT
			in (current_user.admin_permissions or [])
	)

	return {
		"can_create": can_manage,
		"can_edit": can_manage,
		"can_toggle": can_manage,
		"list_url": (
			"/admin/game-systems/list"
			if can_manage
			else "/game-systems"
		),
	}

@router.get("/items/{system_id}", response_model=GameSystemRead, operation_id="getActiveGameSystem")
async def get_active_game_system(system_id: UUID, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	system = await svc.get_game_system(session, system_id)

	if not system.is_active:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Игровая система не найдена",
		)

	return system