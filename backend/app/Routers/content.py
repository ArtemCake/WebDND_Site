# backend/app/Routers/content.py

from Config.imports import (APIRouter, Depends, AsyncSession)
from backend.app.Database.database import get_async_session
from backend.app.Services.Core.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Schemas.content import GameSystemRead
from backend.app.Services import content_service as svc


router = APIRouter(
	prefix="/game-systems",
	tags=["content"]
)

@router.get("", response_model=list[GameSystemRead], operation_id="listGameSystems")
async def list_game_systems(
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.list_active_systems(session, )