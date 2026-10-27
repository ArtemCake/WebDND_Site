# backend/app/Routers/character.py

from Config.imports import (APIRouter, Depends, status, AsyncSession, UUID)
from backend.app.Database.database import get_async_session
from backend.app.Core.csrf import (enforce_csrf,  ensure_csrf_tokens, apply_csrf_tokens)
from backend.app.Services.Core.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Schemas.character import (CharacterCreate, CharacterUpdate, CharacterRead,
                                           CharacterSheetCreate, CharacterSheetUpdate, CharacterSheetRead,
                                           SpellSlotsUpdate, SpellOnSheetUpdate, SpellOnSheetRead, SpellOnSheetIn,
                                           InventoryItemRead, InventoryItemIn, InventoryItemUpdate)

from backend.app.Services import character_service as svc


router = APIRouter(
	prefix="/characters",
	tags=["characters"]
)

@router.get("", response_model=list[CharacterRead], operation_id="listCharacters")
async def list_characters(
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.list_characters(session, current_user.id)

@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED,
             operation_id="createCharacter", dependencies=[Depends(enforce_csrf)])
async def create_character(
		data: CharacterCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.create_character(session, current_user.id, data)

@router.get("/{character_id}", response_model=CharacterRead, operation_id="getCharacter")
async def get_character(
		character_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.get_character(session, character_id, current_user.id)

@router.put("/{character_id}", response_model=CharacterRead, operation_id="updateCharacter",
            dependencies=[Depends(enforce_csrf)])
async def update_character(
		character_id: UUID,
		data: CharacterUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_character(session, character_id, current_user.id, data)

@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteCharacter",
               dependencies=[Depends(enforce_csrf)])
async def delete_character(
		character_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await svc.delete_character(session, character_id, current_user.id)

@router.post("/{character_id}/sheets", response_model=CharacterSheetRead,
             status_code=status.HTTP_201_CREATED, operation_id="createCharacterSheet",
             dependencies=[Depends(enforce_csrf)])
async def create_character_sheet(
		character_id: UUID,
		data: CharacterSheetCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	data.character_id = character_id
	return await svc.create_character_sheet(session, current_user.id, data)

@router.get("/sheets/{sheet_id}", response_model=CharacterSheetRead, operation_id="getCharacterSheet")
async def get_character_sheet(
		sheet_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.get_character_sheet(session, sheet_id, current_user.id)

@router.patch("/sheets/{sheet_id}", response_model=CharacterSheetRead, operation_id="updateCharacterSheet",
              dependencies=[Depends(enforce_csrf)])
async def update_character_sheet(
		sheet_id: UUID,
		data: CharacterSheetUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await svc.update_character_sheet(session, sheet_id, current_user.id, data)

@router.post("/sheets/{sheet_id}/spells", response_model=SpellOnSheetRead,
             status_code=status.HTTP_201_CREATED, operation_id="addSpellToSheet",
             dependencies=[Depends(enforce_csrf)])
async def add_spell_to_sheet(sheet_id: UUID, data: SpellOnSheetIn,
                             session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.add_spell_to_sheet(session, sheet_id, current_user.id, data)

@router.patch("/sheets/{sheet_id}/spells/{spell_link_id}", response_model=SpellOnSheetRead,
              operation_id="updateSheetSpell", dependencies=[Depends(enforce_csrf)])
async def update_sheet_spell(sheet_id: UUID, spell_link_id: UUID, data: SpellOnSheetUpdate,
                             session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.update_sheet_spell(session, sheet_id, spell_link_id, current_user.id, data)

@router.delete("/sheets/{sheet_id}/spells/{spell_link_id}", status_code=status.HTTP_204_NO_CONTENT,
               operation_id="removeSpellFromSheet", dependencies=[Depends(enforce_csrf)])
async def remove_spell_from_sheet(sheet_id: UUID, spell_link_id: UUID,
                                  session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	await svc.remove_spell_from_sheet(session, sheet_id, spell_link_id, current_user.id)

@router.patch("/sheets/{sheet_id}/spell-slots", response_model=CharacterSheetRead,
              operation_id="updateSpellSlots", dependencies=[Depends(enforce_csrf)])
async def update_spell_slots(sheet_id: UUID, data: SpellSlotsUpdate,
                             session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.update_spell_slots(session, sheet_id, current_user.id, data.slots)

@router.post("/sheets/{sheet_id}/inventory", response_model=InventoryItemRead,
             status_code=status.HTTP_201_CREATED, operation_id="addItemToInventory",
             dependencies=[Depends(enforce_csrf)])
async def add_item_to_inventory(sheet_id: UUID, data: InventoryItemIn,
                                session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.add_item_to_inventory(session, sheet_id, current_user.id, data)

@router.patch("/sheets/{sheet_id}/inventory/{item_id}", response_model=InventoryItemRead,
              operation_id="updateInventoryItem", dependencies=[Depends(enforce_csrf)])
async def update_inventory_item(sheet_id: UUID, item_id: UUID, data: InventoryItemUpdate,
                                session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	return await svc.update_inventory_item(session, sheet_id, item_id, current_user.id, data)

@router.delete("/sheets/{sheet_id}/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT,
               operation_id="removeItemFromInventory", dependencies=[Depends(enforce_csrf)])
async def remove_item_from_inventory(sheet_id: UUID, item_id: UUID,
                                     session: AsyncSession = Depends(get_async_session), current_user: User = Depends(get_current_user)):
	await svc.remove_item_from_inventory(session, sheet_id, item_id, current_user.id)