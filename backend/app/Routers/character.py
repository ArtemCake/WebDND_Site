# backend/app/Routers/character.py

from Config.imports import (APIRouter, Depends, status, AsyncSession, UUID)
from backend.app.database.database import get_async_session
from backend.app.core.csrf import enforce_csrf
from backend.app.Services.user_service import get_current_user
from backend.app.database.models.core.user import User
from backend.app.schemas.character import (CharacterCreate, CharacterUpdate, CharacterRead,
	CharacterSheetCreate, CharacterSheetUpdate, CharacterSheetRead)
from backend.app.Services import character_service as svc


router = APIRouter(
	prefix="/characters",
	tags=["characters"]
)

@router.get("", response_model=list[CharacterRead])
async def list_characters(
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.list_characters(session, current_user.id)

@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
async def create_character(
		data: CharacterCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.create_character(session, current_user.id, data)

@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(
		character_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.get_character(session, character_id, current_user.id)

@router.put("/{character_id}", response_model=CharacterRead,
            dependencies=[Depends(enforce_csrf)])
async def update_character(
		character_id: UUID,
		data: CharacterUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_character(session, character_id, current_user.id, data)

@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
async def delete_character(
		character_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await svc.delete_character(session, character_id, current_user.id)

@router.post("/{character_id}/sheets", response_model=CharacterSheetRead,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(enforce_csrf)])
async def create_character_sheet(
		character_id: UUID,
		data: CharacterSheetCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	data.base_character_id = character_id
	return await svc.create_character_sheet(session, current_user.id, data)

@router.get("/sheets/{sheet_id}", response_model=CharacterSheetRead)
async def get_character_sheet(
		sheet_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.get_character_sheet(session, sheet_id, current_user.id)

@router.patch("/sheets/{sheet_id}", response_model=CharacterSheetRead,
              dependencies=[Depends(enforce_csrf)])
async def update_character_sheet(
		sheet_id: UUID,
		data: CharacterSheetUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_character_sheet(session, sheet_id, current_user.id, data)