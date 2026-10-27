# backend/app/Routers/game_state.py

from Config.imports import (APIRouter, Depends, status, AsyncSession, UUID)
from backend.app.Database.database import get_async_session
from backend.app.Core.csrf import (enforce_csrf,  ensure_csrf_tokens, apply_csrf_tokens)
from backend.app.Services.Core.user_service import get_current_user
from backend.app.Database.Models.Core.user import User
from backend.app.Schemas.maps import TokenCreate, TokenUpdate, TokenMove, TokenRead
from backend.app.Schemas.lobby import DiceRollIn, DiceRollRead
from backend.app.Services.Games import dice_service, initiative_service, token_service

router = APIRouter(
	prefix="/sessions",
	tags=["game_state"]
)

# --- Tokens ---

@router.post("/tokens", response_model=TokenRead, status_code=status.HTTP_201_CREATED,
             operation_id="createToken", dependencies=[Depends(enforce_csrf)])
async def create_token(
		data: TokenCreate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await token_service.create_token(session, current_user.id, data)

# GET /sessions/{session_id}/tokens
@router.get("/{session_id}/tokens", response_model=list[TokenRead], operation_id="listTokens")
async def list_tokens(session_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await token_service.list_tokens_for_session(
		session,
		session_id,
		current_user.id,
	)

@router.patch("/tokens/{token_id}", response_model=TokenRead, operation_id="updateToken",
              dependencies=[Depends(enforce_csrf)])
async def update_token(
		token_id: UUID,
		data: TokenUpdate,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await token_service.update_token(session, token_id, current_user.id, data)

@router.post("/tokens/{token_id}/move", response_model=TokenRead, operation_id="moveToken",
             dependencies=[Depends(enforce_csrf)])
async def move_token(
		token_id: UUID,
		data: TokenMove,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await token_service.move_token(session, token_id, current_user.id, data)

@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteToken",
               dependencies=[Depends(enforce_csrf)])
async def delete_token(
		token_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await token_service.delete_token(session, token_id, current_user.id)

# --- Initiative / combat ---

@router.get(
	"/{session_id}/combat",
	operation_id="getCombatState",
)
async def get_combat_state(session_id: UUID, session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user)):
	return await initiative_service.get_combat_state(session, session_id, current_user.id)

@router.post("/{session_id}/combat/start", operation_id="startCombat", dependencies=[Depends(enforce_csrf)])
async def start_combat(
		session_id: UUID,
		combatants: list[dict],
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	tracker = await initiative_service.start_combat(session, session_id, current_user.id, combatants)
	return {"session_id": tracker.session_id, "turn_order": tracker.turn_order_json,
	        "current_index": tracker.current_index, "round_number": tracker.round_number}

@router.post("/{session_id}/combat/next-turn", operation_id="nextTurn", dependencies=[Depends(enforce_csrf)])
async def next_turn(
		session_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	tracker = await initiative_service.next_turn(session, session_id, current_user.id)
	return {"session_id": tracker.session_id, "turn_order": tracker.turn_order_json,
	        "current_index": tracker.current_index, "round_number": tracker.round_number}

@router.post("/{session_id}/combat/end", status_code=status.HTTP_204_NO_CONTENT, operation_id="endCombat",
             dependencies=[Depends(enforce_csrf)])
async def end_combat(
		session_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	await initiative_service.end_combat(session, session_id, current_user.id)

# --- Dice ---

@router.post("/{session_id}/roll", response_model=DiceRollRead, status_code=status.HTTP_201_CREATED,
             operation_id="rollDice", dependencies=[Depends(enforce_csrf)])
async def roll_dice(
		session_id: UUID,
		data: DiceRollIn,
		party_id: UUID | None = None,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await dice_service.roll_dice(session, session_id, current_user.id, party_id, data)

# GET /sessions/{session_id}/rolls
@router.get("/{session_id}/rolls",response_model=list[DiceRollRead],operation_id="listRolls")
async def list_rolls(
		session_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
):
	return await dice_service.list_session_rolls(
		session,
		session_id,
		current_user.id,
	)