# backend/app/Services/admin_service.py

"""Сервис административной панели: пользователи, жалобы, аудит-лог.
Доступ к каждому разделу проверяется через require_permission — отдельно
от самой роли admin, согласно гранулярной модели прав."""

from Config.imports import AsyncSession, select, Depends, HTTPException, status, func
from backend.app.Database.Models.Core.user import User
from backend.app.Database.Models.Systems.system import AuditLog, ContentReport
from backend.app.Enums.enums_BD import SystemRole, AdminPermission
from backend.app.Services.Core.user_service import get_current_user


PAGE_SIZE = 25

async def get_admin_user(user: User = Depends(get_current_user)) -> User:
	"""Базовый порог входа в /admin: нужна сама роль admin."""
	if SystemRole.ADMIN not in (user.roles or []):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора.")
	return user

def require_permission(permission: AdminPermission):
	"""Фабрика зависимости: пускает только администратора, которому
	явно выдано конкретное право раздела."""
	async def _dependency(user: User = Depends(get_admin_user)) -> User:
		if permission not in (user.admin_permissions or []):
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail=f"У вас нет доступа к разделу «{permission.value}». "
				       "Обратитесь к администратору с полными правами."
			)
		return user
	return _dependency

async def list_users(session: AsyncSession, search: str | None = None, page: int = 1):
	query = select(User)
	count_query = select(func.count()).select_from(User)
	if search:
		pattern = f"%{search}%"
		condition = (User.nickname.ilike(pattern)) | (User.email.ilike(pattern))
		query = query.where(condition)
		count_query = count_query.where(condition)

	total = (await session.execute(count_query)).scalar_one()
	query = query.order_by(User.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
	users = (await session.execute(query)).scalars().all()
	return users, total

async def admin_set_roles(session: AsyncSession, target: User, roles: list[SystemRole]) -> User:
	if not roles:
		raise ValueError("У пользователя должна остаться хотя бы одна роль.")
	target.roles = list(dict.fromkeys(roles))
	# Роль admin снята — права разделов тоже теряют смысл, обнуляем,
	# чтобы они не висели молча и не выдавались повторно при возврате роли.
	if SystemRole.ADMIN not in target.roles:
		target.admin_permissions = []
	await session.commit()
	await session.refresh(target)
	return target

async def admin_set_permissions(session: AsyncSession, target: User, permissions: list[AdminPermission]) -> User:
	target.admin_permissions = list(dict.fromkeys(permissions))
	await session.commit()
	await session.refresh(target)
	return target

async def list_reports(session: AsyncSession, status_filter: str | None = None, page: int = 1):
	query = select(ContentReport)
	count_query = select(func.count()).select_from(ContentReport)
	if status_filter:
		query = query.where(ContentReport.status == status_filter)
		count_query = count_query.where(ContentReport.status == status_filter)

	total = (await session.execute(count_query)).scalar_one()
	query = query.order_by(ContentReport.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
	reports = (await session.execute(query)).scalars().all()
	return reports, total

async def get_report_by_id(session: AsyncSession, report_id) -> ContentReport | None:
	result = await session.execute(select(ContentReport).where(ContentReport.id == report_id))
	return result.scalar_one_or_none()

async def update_report(session: AsyncSession, report: ContentReport, new_status: str, note: str | None) -> ContentReport:
	report.status = new_status
	if note is not None:
		report.moderator_note = note
	await session.commit()
	await session.refresh(report)
	return report

async def list_audit_logs(session: AsyncSession, page: int = 1):
	query = select(AuditLog).order_by(AuditLog.created_at.desc())
	count_query = select(func.count()).select_from(AuditLog)
	total = (await session.execute(count_query)).scalar_one()
	query = query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
	logs = (await session.execute(query)).scalars().all()
	return logs, total
