# backend/app/Routers/game_system_engines.py

"""Административный API движков и происхождения правил систем.

Подключается внутрь admin.router.
Все пути ниже получают префикс /admin.
"""

from Config.imports import (APIRouter, AsyncSession, Depends, HTTPException, Query, Response, UUID)
from backend.app.Core.csrf import enforce_csrf
from backend.app.Database.database import get_async_session
from backend.app.Database.Models.Core.user import User
from backend.app.Enums.enums_BD import AdminPermission
from backend.app.Services.admin_service import require_permission
from backend.app.Schemas.game_rules import (GameSystemRulesDraftRead, GameSystemRulesPublish, GameSystemRulesVersionRead)
from backend.app.Schemas.game_system_editor import GameSystemEditorRead
from backend.app.Schemas.game_system_origin import (GameSystemDraftEngineSet, GameSystemFromEngineCreate)
from backend.app.Schemas.rule_engines import (RuleEngineCreate, RuleEngineDraftRead, RuleEngineDraftUpdate, RuleEngineEditorRead,
                                              RuleEnginePage, RuleEnginePublish, RuleEngineVersionPage, RuleEngineVersionRead)
from backend.app.Services.GameSystems import (editor_service, rule_engine_service as engines, rules_service)


def _no_store(response: Response) -> None:
	response.headers["Cache-Control"] = "no-store"

def _content_actor_id(actor: User = Depends(require_permission(AdminPermission.CONTENT))) -> UUID:
	# Проверка роли и разрешения выполняется require_permission.
	# Идентификатор берём только из аутентифицированного пользователя.
	actor_id = getattr(actor, "id", None)

	if not isinstance(actor_id, UUID):
		raise HTTPException(
			status_code=401,
			detail="Требуется авторизованный пользователь.",
		)

	return actor_id

router = APIRouter(
	dependencies=[Depends(_no_store)],
)

@router.get("/rule-engines", response_model=RuleEnginePage, operation_id="adminListRuleEngines")
async def list_engines(owned_only: bool = False, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
		session: AsyncSession = Depends(get_async_session), actor_id: UUID = Depends(_content_actor_id)):
	return await engines.list_rule_engines(
		session,
		actor_id,
		owned_only=owned_only,
		limit=limit,
		offset=offset,
	)

@router.post("/rule-engines", response_model=RuleEngineEditorRead, status_code=201, operation_id="adminCreateRuleEngine",
	dependencies=[Depends(enforce_csrf)])
async def create_engine(data: RuleEngineCreate, session: AsyncSession = Depends(get_async_session), actor_id: UUID = Depends(_content_actor_id)):
	return await engines.create_engine_with_draft(
		session,
		actor_id,
		data,
	)

@router.get("/rule-engines/{engine_id}/draft", response_model=RuleEngineDraftRead, operation_id="adminGetRuleEngineDraft")
async def get_engine_draft(engine_id: UUID, session: AsyncSession = Depends(get_async_session), actor_id: UUID = Depends(_content_actor_id)):
	return await engines.get_engine_draft(
		session,
		engine_id,
		actor_id,
	)

@router.put("/rule-engines/{engine_id}/draft", response_model=RuleEngineDraftRead, operation_id="adminSaveRuleEngineDraft", dependencies=[Depends(enforce_csrf)])
async def save_engine_draft(engine_id: UUID, data: RuleEngineDraftUpdate, session: AsyncSession = Depends(get_async_session),
		actor_id: UUID = Depends(_content_actor_id)):
	return await engines.update_engine_draft(
		session,
		engine_id,
		actor_id,
		data,
	)

@router.post("/rule-engines/{engine_id}/publish", response_model=RuleEngineVersionRead, status_code=201, operation_id="adminPublishRuleEngine",
	dependencies=[Depends(enforce_csrf)])
async def publish_engine(engine_id: UUID, data: RuleEnginePublish, session: AsyncSession = Depends(get_async_session),
		actor_id: UUID = Depends(_content_actor_id)):
	return await engines.publish_engine_version(
		session,
		engine_id,
		actor_id,
		data,
	)

@router.get("/rule-engines/{engine_id}/versions", response_model=RuleEngineVersionPage, operation_id="adminListRuleEngineVersions")
async def list_versions(engine_id: UUID, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), session: AsyncSession = Depends(get_async_session),
		actor_id: UUID = Depends(_content_actor_id)):
	return await engines.list_engine_versions(
		session,
		engine_id,
		actor_id,
		limit=limit,
		offset=offset,
	)

@router.get("/rule-engines/{engine_id}/versions/{version_id}", response_model=RuleEngineVersionRead, operation_id="adminGetRuleEngineVersion")
async def get_version(engine_id: UUID, version_id: UUID, session: AsyncSession = Depends(get_async_session),
		actor_id: UUID = Depends(_content_actor_id)):
	return await engines.get_engine_version(
		session,
		engine_id,
		version_id,
		actor_id,
	)

@router.post("/game-systems/from-engine", response_model=GameSystemEditorRead, status_code=201, operation_id="adminCreateGameSystemFromEngine",
	dependencies=[Depends(enforce_csrf)])
async def create_system(data: GameSystemFromEngineCreate, session: AsyncSession = Depends(get_async_session), actor_id: UUID = Depends(_content_actor_id)):
	return await editor_service.create_system_from_engine(
		session,
		actor_id,
		data,
	)

@router.put("/game-systems/{system_id}/rules/engine", response_model=GameSystemRulesDraftRead, operation_id="adminSetGameSystemRulesEngine",
	dependencies=[Depends(enforce_csrf)])
async def save_system_origin(system_id: UUID, data: GameSystemDraftEngineSet, session: AsyncSession = Depends(get_async_session),
		actor_id: UUID = Depends(_content_actor_id)):
	return await rules_service.set_rules_draft_engine(
		session,
		system_id,
		actor_id,
		data,
	)

@router.post("/game-systems/{system_id}/rules/publish", response_model=GameSystemRulesVersionRead, status_code=201,
	operation_id="adminPublishGameSystemRules", dependencies=[Depends(enforce_csrf)])
async def publish_system_rules(system_id: UUID, data: GameSystemRulesPublish, session: AsyncSession = Depends(get_async_session),
		actor_id: UUID = Depends(_content_actor_id)):
	# actor_id здесь нужен для обязательного прохождения
	# административной проверки перед вызовом сервиса.
	return await rules_service.publish_rules_version(
		session,
		system_id,
		data,
	)