# backend/app/Routers/admin.py

"""Административная панель: пользователи, жалобы на контент, аудит-лог."""

from Config.Config import settings
from backend.app.Services.GameSystems.delete_service import (delete_game_system)
from Config.imports import (APIRouter, Depends, Request, HTMLResponse, JSONResponse, RedirectResponse,
                            status, HTTPException, CsrfProtect, Form, UUID, AsyncSession, Response)
from backend.app.Routers.game_system_engines import (router as game_system_engines_router)
from backend.app.Database.database import get_async_session
from backend.app.Database.Models.Core.user import User
from backend.app.Enums.enums_BD import SystemRole, AdminPermission
from backend.app.Services.Core.user_service import soft_delete_user, hard_delete_user, get_user_by_id
from backend.app.Services.admin_service import (get_admin_user, require_permission, list_users, admin_set_roles, admin_set_permissions,
	list_reports, update_report, get_report_by_id, list_audit_logs)
from backend.app.Core.csrf import (enforce_csrf,  ensure_csrf_tokens, apply_csrf_tokens)
from backend.app.Schemas.content import (GameSystemCreate,GameSystemUpdate,	GameSystemAdminRead)
from backend.app.Services import content_service
from backend.app.Schemas.game_rules import (CheckPreviewInput, CheckResult, AttributePreviewInput, GameSystemRulesDraftCreate,
                                            GameSystemRulesDraftUpdate, GameSystemRulesDraftRead, GameSystemRulesDraftState, GameSystemRulesPublishedState)
from backend.app.Services.GameSystems.rules_presets import (list_rules_presets, create_calculation_profile)
from backend.app.Services.GameSystems.rules_engine import (evaluate_check)
from backend.app.Schemas.rule_calculations import (AttributePreviewResult)
from backend.app.Services.GameSystems.attribute_engine import (evaluate_attributes)
from backend.app.Services.GameSystems import rules_service, editor_service
from backend.app.Schemas.game_system_editor import (GameSystemEditorCreate, GameSystemEditorUpdate, GameSystemEditorRead)


router = APIRouter(
	prefix="/admin",
    tags=["admin"]
)

ROLE_LABELS = {
	SystemRole.PLAYER: "Игрок", SystemRole.MASTER: "Мастер (ведущий)",
	SystemRole.EDITOR: "Редактор контента", SystemRole.ADMIN: "Администратор",
}
PERMISSION_LABELS = {
	AdminPermission.USERS: "Пользователи", AdminPermission.CONTENT: "Контент",
	AdminPermission.REPORTS: "Жалобы", AdminPermission.AUDIT: "Аудит-лог",
	AdminPermission.SYSTEM: "Система",
}

@router.get("/", response_class=HTMLResponse, name="admin_dashboard_get")
async def admin_dashboard(request: Request, user: User = Depends(get_admin_user), csrf_protect: CsrfProtect = Depends()):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"permission_labels": PERMISSION_LABELS,
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/dashboard.html", context=context)
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/users", response_class=HTMLResponse, name="admin_users_get")
async def admin_users_page(request: Request, search: str | None = None, page: int = 1,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(require_permission(AdminPermission.USERS)),
		csrf_protect: CsrfProtect = Depends()):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	users, total = await list_users(session, search=search, page=page)
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"users": users, "total": total, "page": page, "search": search or "",
		"role_labels": ROLE_LABELS, "all_roles": list(SystemRole),
		"all_permissions": list(AdminPermission), "permission_labels": PERMISSION_LABELS,
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/users.html", context=context)
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.patch("/users/{user_id}/roles", response_class=JSONResponse, operation_id="adminUpdateUserRoles", dependencies=[Depends(enforce_csrf)])
async def admin_update_user_roles(user_id: UUID, roles: list[SystemRole] = Form([]), session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.USERS))):
	target = await get_user_by_id(session, str(user_id))
	if not target:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")

	try:
		updated = await admin_set_roles(session, target, roles)
	except ValueError as e:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

	return {"message": "Роли обновлены.", "roles": [r.value for r in updated.roles]}

@router.patch("/users/{user_id}/permissions", response_class=JSONResponse, operation_id="adminUpdateUserPermissions", dependencies=[Depends(enforce_csrf)])
async def admin_update_user_permissions(user_id: UUID, permissions: list[AdminPermission] = Form([]),
		session: AsyncSession = Depends(get_async_session), actor: User = Depends(require_permission(AdminPermission.USERS))):
	target = await get_user_by_id(session, str(user_id))
	if not target:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
	if SystemRole.ADMIN not in (target.roles or []):
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Права разделов назначаются только пользователям с ролью «Администратор»."
		)

	updated = await admin_set_permissions(session, target, permissions)
	return {"message": "Права обновлены.", "permissions": [p.value for p in updated.admin_permissions]}

@router.post("/users/{user_id}/delete", response_class=JSONResponse, operation_id="adminDeleteUser", dependencies=[Depends(enforce_csrf)])
async def admin_delete_user(user_id: UUID, permanent: bool = Form(False), session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.USERS))):
	if user_id == actor.id:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Свой аккаунт удаляйте через настройки профиля, а не через админ-панель."
		)

	target = await get_user_by_id(session, str(user_id))
	if not target:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")

	if permanent:
		await hard_delete_user(session, str(user_id))
		return {"message": "Пользователь удалён навсегда."}

	ok = await soft_delete_user(session, str(user_id))
	if not ok:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже деактивирован.")
	return {"message": "Пользователь деактивирован."}

@router.get("/reports", response_class=HTMLResponse, name="admin_reports_get")
async def admin_reports_page(request: Request, status_filter: str | None = None, page: int = 1,
		session: AsyncSession = Depends(get_async_session), user: User = Depends(require_permission(AdminPermission.REPORTS)),
		csrf_protect: CsrfProtect = Depends()):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	reports, total = await list_reports(session, status_filter=status_filter, page=page)
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"reports": reports, "total": total, "page": page, "status_filter": status_filter or "",
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/reports.html", context=context)
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.patch("/reports/{report_id}", response_class=JSONResponse, operation_id="adminUpdateReport", dependencies=[Depends(enforce_csrf)])
async def admin_update_report(report_id: UUID,  new_status: str = Form(...), moderator_note: str | None = Form(None),
		session: AsyncSession = Depends(get_async_session), actor: User = Depends(require_permission(AdminPermission.REPORTS))):
	report = await get_report_by_id(session, report_id)
	if not report:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Жалоба не найдена.")

	updated = await update_report(session, report, new_status=new_status, note=moderator_note)
	return {"message": "Жалоба обновлена.", "status": updated.status}

@router.get("/audit", response_class=HTMLResponse, name="admin_audit_get")
async def admin_audit_page(request: Request, page: int = 1, session: AsyncSession = Depends(get_async_session),
		user: User = Depends(require_permission(AdminPermission.AUDIT)), csrf_protect: CsrfProtect = Depends()):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	logs, total = await list_audit_logs(session, page=page)
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"logs": logs, "total": total, "page": page,
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/audit.html", context=context)
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

# --- Игровые системы ---

@router.get("/game-systems", response_class=RedirectResponse, name="admin_game_systems_get", operation_id="adminGameSystemsPage")
async def admin_game_systems_page():
	return RedirectResponse(
		url="/game-systems/catalog",
		status_code=status.HTTP_303_SEE_OTHER,
		headers={"Cache-Control": "no-store"},
	)

# Статический путь списка обязательно регистрируем раньше
# параметризованного /game-systems/{system_id}.
@router.get("/game-systems/list", response_model=list[GameSystemAdminRead], operation_id="adminListGameSystems")
async def admin_list_game_systems(session: AsyncSession = Depends(get_async_session), actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	return await content_service.list_all_systems(session)

@router.get("/game-systems/{system_id}", response_model=GameSystemAdminRead, operation_id="adminGetGameSystem")
async def admin_get_game_system(system_id: UUID, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	return await content_service.get_game_system(session, system_id)

@router.post("/game-systems", response_model=GameSystemAdminRead, status_code=status.HTTP_201_CREATED, operation_id="adminCreateGameSystem",
             dependencies=[Depends(enforce_csrf)])
async def admin_create_game_system(data: GameSystemCreate, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	return await content_service.create_game_system(session, data)

@router.patch("/game-systems/{system_id}", response_model=GameSystemAdminRead, operation_id="adminUpdateGameSystem", dependencies=[Depends(enforce_csrf)])
async def admin_update_game_system(system_id: UUID, data: GameSystemUpdate, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	return await content_service.update_game_system(
		session,
		system_id,
		data,
	)

@router.get("/game-systems/rules/presets", operation_id="adminListGameRulesPresets")
async def admin_list_game_rules_presets(actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	return list_rules_presets()

@router.post("/game-systems/rules/preview", response_model=CheckResult, operation_id="adminPreviewGameRules", dependencies=[Depends(enforce_csrf)])
async def admin_preview_game_rules(data: CheckPreviewInput, actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	try:
		return evaluate_check(data.rules, data.check)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail=str(exc),
		) from exc

@router.post("/game-systems/rules/attributes/preview", response_model=AttributePreviewResult, operation_id="adminPreviewGameSystemAttributes",
             dependencies=[Depends(enforce_csrf)])
async def admin_preview_game_system_attributes(data: AttributePreviewInput, actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	"""Рассчитать характеристики без сохранения и игровых действий."""

	try:
		return evaluate_attributes(data)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=str(exc),
		) from exc

@router.get("/game-systems/rules/calculation-presets", operation_id="adminListCalculationPresets")
async def admin_list_calculation_presets(response: Response,actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	return [
		{
			"code": preset["code"],
			"name": preset["name"],
			"rules": create_calculation_profile(
				preset["code"],
			).model_dump(mode="json"),
		}
		for preset in list_rules_presets()
	]

@router.get("/game-systems/{system_id}/rules/draft", response_model=GameSystemRulesDraftState, operation_id="adminGetGameSystemRulesDraft")
async def admin_get_game_system_rules_draft(system_id: UUID, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	# Сначала отличаем отсутствующую систему от отсутствующего
	# черновика. Проверка прав выполнена зависимостью выше.
	await content_service.get_game_system(session, system_id)

	try:
		draft = await rules_service.get_rules_draft(
			session,
			system_id,
		)
	except HTTPException as exc:
		if exc.status_code != status.HTTP_404_NOT_FOUND:
			raise

		draft = None

	return GameSystemRulesDraftState(draft=draft)

@router.post("/game-systems/{system_id}/rules/draft", response_model=GameSystemRulesDraftRead, status_code=status.HTTP_201_CREATED,
	operation_id="adminCreateGameSystemRulesDraft", dependencies=[Depends(enforce_csrf)])
async def admin_create_game_system_rules_draft(system_id: UUID, data: GameSystemRulesDraftCreate, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	return await rules_service.create_rules_draft(
		session,
		system_id,
		data,
	)

@router.patch("/game-systems/{system_id}/rules/draft", response_model=GameSystemRulesDraftRead, operation_id="adminUpdateGameSystemRulesDraft", dependencies=[Depends(enforce_csrf)])
async def admin_update_game_system_rules_draft(system_id: UUID, data: GameSystemRulesDraftUpdate, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	return await rules_service.update_rules_draft(
		session,
		system_id,
		data,
	)

@router.post("/game-systems/editor/create", response_model=GameSystemEditorRead, status_code=status.HTTP_201_CREATED,
	operation_id="adminCreateGameSystemWithDraft", dependencies=[Depends(enforce_csrf)])
async def admin_create_game_system_with_draft(data: GameSystemEditorCreate, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	return await editor_service.create_system_with_draft(
		session,
		data,
	)

@router.put("/game-systems/{system_id}/editor", response_model=GameSystemEditorRead, operation_id="adminSaveGameSystemWithDraft",
	dependencies=[Depends(enforce_csrf)])
async def admin_save_game_system_with_draft(system_id: UUID, data: GameSystemEditorUpdate, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	return await editor_service.update_system_with_draft(
		session,
		system_id,
		data,
	)

@router.delete("/game-systems/{system_id}", operation_id="adminDeleteGameSystem", dependencies=[Depends(enforce_csrf)])
async def admin_delete_game_system(system_id: UUID, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	return await delete_game_system(session, system_id)

@router.get("/game-systems/{system_id}/rules/latest", response_model=GameSystemRulesPublishedState, operation_id="adminGetGameSystemPublishedRules")
async def admin_get_game_system_published_rules(system_id: UUID, response: Response, session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(require_permission(AdminPermission.CONTENT))):
	response.headers["Cache-Control"] = "no-store"

	# Администратор может просматривать и неактивные системы.
	# Отсутствующую систему отличаем от отсутствующей публикации.
	await content_service.get_game_system(session, system_id)

	version = await rules_service.get_latest_rules_version(
		session,
		system_id,
	)

	return GameSystemRulesPublishedState(version=version)

router.include_router(game_system_engines_router)