# backend/app/Routers/admin.py

"""Административная панель: пользователи, жалобы на контент, аудит-лог."""

from Config.Config import settings
from Config.imports import (APIRouter, Depends, Request, HTMLResponse, JSONResponse,
                            status, HTTPException, CsrfProtect, Form, UUID, AsyncSession)
from backend.app.Database.database import get_async_session
from backend.app.Database.Models.Core.user import User
from backend.app.Enums.enums_BD import SystemRole, AdminPermission
from backend.app.Services.user_service import soft_delete_user, hard_delete_user, get_user_by_id
from backend.app.Services.admin_service import (get_admin_user, require_permission, list_users, admin_set_roles, admin_set_permissions,
	list_reports, update_report, get_report_by_id, list_audit_logs)
from backend.app.Core.csrf import enforce_csrf
from backend.app.Schemas.content import (GameSystemCreate,GameSystemUpdate,	GameSystemAdminRead)
from backend.app.Services import content_service


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
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"permission_labels": PERMISSION_LABELS,
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/dashboard.html", context=context)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.get("/users", response_class=HTMLResponse, name="admin_users_get")
async def admin_users_page(
		request: Request, search: str | None = None, page: int = 1,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(require_permission(AdminPermission.USERS)),
		csrf_protect: CsrfProtect = Depends(),
):
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	users, total = await list_users(session, search=search, page=page)
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"users": users, "total": total, "page": page, "search": search or "",
		"role_labels": ROLE_LABELS, "all_roles": list(SystemRole),
		"all_permissions": list(AdminPermission), "permission_labels": PERMISSION_LABELS,
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/users.html", context=context)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.patch("/users/{user_id}/roles", response_class=JSONResponse, operation_id="adminUpdateUserRoles", dependencies=[Depends(enforce_csrf)])
async def admin_update_user_roles(
		user_id: UUID,
		roles: list[SystemRole] = Form([]),
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.USERS)
		),
):
	target = await get_user_by_id(session, str(user_id))
	if not target:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")

	try:
		updated = await admin_set_roles(session, target, roles)
	except ValueError as e:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

	return {"message": "Роли обновлены.", "roles": [r.value for r in updated.roles]}

@router.patch("/users/{user_id}/permissions", response_class=JSONResponse, operation_id="adminUpdateUserPermissions", dependencies=[Depends(enforce_csrf)])
async def admin_update_user_permissions(
		user_id: UUID,
		permissions: list[AdminPermission] = Form([]),
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.USERS)
		),
):
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
async def admin_delete_user(
		user_id: UUID, permanent: bool = Form(False),
		session: AsyncSession = Depends(get_async_session),
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
async def admin_reports_page(
		request: Request, status_filter: str | None = None, page: int = 1,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(require_permission(AdminPermission.REPORTS)),
		csrf_protect: CsrfProtect = Depends(),
):
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	reports, total = await list_reports(session, status_filter=status_filter, page=page)
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"reports": reports, "total": total, "page": page, "status_filter": status_filter or "",
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/reports.html", context=context)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.patch("/reports/{report_id}", response_class=JSONResponse, operation_id="adminUpdateReport", dependencies=[Depends(enforce_csrf)])
async def admin_update_report(
		report_id: UUID,
		new_status: str = Form(...),
		moderator_note: str | None = Form(None),
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.REPORTS)
		),
):
	report = await get_report_by_id(session, report_id)
	if not report:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Жалоба не найдена.")

	updated = await update_report(session, report, new_status=new_status, note=moderator_note)
	return {"message": "Жалоба обновлена.", "status": updated.status}

@router.get("/audit", response_class=HTMLResponse, name="admin_audit_get")
async def admin_audit_page(
		request: Request, page: int = 1,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(require_permission(AdminPermission.AUDIT)),
		csrf_protect: CsrfProtect = Depends(),
):
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	logs, total = await list_audit_logs(session, page=page)
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"logs": logs, "total": total, "page": page,
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="admin/audit.html", context=context)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

# --- Игровые системы ---

# GET /admin/game-systems/list
@router.get(
	"/game-systems/list",
	response_model=list[GameSystemAdminRead],
	operation_id="adminListGameSystems",
)
async def admin_list_game_systems(
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.CONTENT)
		),
):
	return await content_service.list_all_systems(session)

# GET /admin/game-systems/{system_id}
@router.get(
	"/game-systems/{system_id}",
	response_model=GameSystemAdminRead,
	operation_id="adminGetGameSystem",
)
async def admin_get_game_system(
		system_id: UUID,
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.CONTENT)
		),
):
	return await content_service.get_game_system(
		session,
		system_id,
	)

# POST /admin/game-systems
@router.post(
	"/game-systems",
	response_model=GameSystemAdminRead,
	status_code=status.HTTP_201_CREATED,
	operation_id="adminCreateGameSystem",
	dependencies=[Depends(enforce_csrf)],
)
async def admin_create_game_system(
		data: GameSystemCreate,
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.CONTENT)
		),
):
	return await content_service.create_game_system(
		session,
		data,
	)

# PATCH /admin/game-systems/{system_id}
@router.patch("/game-systems/{system_id}",response_model=GameSystemAdminRead,operation_id="adminUpdateGameSystem",dependencies=[Depends(enforce_csrf)])
async def admin_update_game_system(
		system_id: UUID,
		data: GameSystemUpdate,
		session: AsyncSession = Depends(get_async_session),
		actor: User = Depends(
			require_permission(AdminPermission.CONTENT)
		),
):
	return await content_service.update_game_system(
		session,
		system_id,
		data,
	)

# GET /admin/game-systems
@router.get("/game-systems",response_class=HTMLResponse,name="admin_game_systems_get",operation_id="adminGameSystemsPage")
async def admin_game_systems_page(
		request: Request,
		user: User = Depends(
			require_permission(AdminPermission.CONTENT)
		),
		csrf_protect: CsrfProtect = Depends(),
):
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

	context = {
		"user": user,
		"project_name": settings.PROJECT_NAME,
		"csrf_token": csrf_token,
	}

	response = request.app.state.templates.TemplateResponse(
		request=request,
		name="admin/game_systems.html",
		context=context,
	)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

