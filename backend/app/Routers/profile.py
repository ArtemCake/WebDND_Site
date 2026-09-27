# backend/app/Routers/profile.py

from backend.app.database.database import get_async_session
from Config.Config import settings
from Config.imports import (JSONResponse, HTMLResponse, APIRouter, Depends, HTTPException,
	status, UploadFile, File, Request, EmailStr, BaseModel, Field,
	AsyncSession, UUID, jwt, JWTError, datetime, ValidationError,
	asyncio)
from backend.app.database.models.core.user import User
from backend.app.Services.user_service import (update_user_profile, change_password, get_current_user)
from app.schemas.auth import ChangePasswordRequest


router = APIRouter(
	prefix="/profile",
	tags=["profile"],
)

env_lock = asyncio.Lock()

# --- DTO МОДЕЛИ (Data Transfer Objects) ---

class ProfileSettingsDTO(BaseModel):
	"""Настройки визуального профиля пользователя."""
	theme_color: str | None = Field(default="#a855f7", description="Основной цвет темы")
	background_url: str | None = Field(default=None, description="Ссылка на фоновое изображение")

class ProfileResponseDTO(BaseModel):
	"""Публичные данные профиля для отображения пользователю."""
	id: UUID
	nickname: str
	email: EmailStr
	avatar_url: str | None = None
	is_email_verified: bool
	profile_settings: ProfileSettingsDTO

# --- КОНТРОЛЛЕРЫ (ВЬЮХИ) ---
@router.get("/", response_class=HTMLResponse, name="profile_page_get")
async def get_profile_page(request: Request, user: User = Depends(get_current_user)):
	"""
	Возвращает HTML-страницу личного кабинета.
	"""
	context = {
		"user": user,
		"project_name": settings.PROJECT_NAME
	}
	templates = request.app.state.templates
	return templates.TemplateResponse(request, "profile.html", context)

@router.get("/data", response_model=ProfileResponseDTO, operation_id="getCurrentUserProfile")
async def get_profile_data(user: User = Depends(get_current_user)):
	"""
	Возвращает структурированные данные текущего пользователя в формате JSON.
	Используется фронтендом для динамического обновления интерфейса.
	"""
	settings_dto = ProfileSettingsDTO(**(user.profile_settings or {}))

	return ProfileResponseDTO(
		id=user.id,
		nickname=user.nickname,
		email=user.email,
		avatar_url=user.avatar_url,
		is_email_verified=user.is_email_verified,
		profile_settings=settings_dto
	)

@router.put("/update", response_class=JSONResponse, status_code=status.HTTP_200_OK, operation_id="updateUserProfile")
async def api_update_profile(
		# Оставляем Form(...) так как htmx отправляет multipart/form-data
		nickname: str = Form(...),
		email: EmailStr = Form(...),
		avatar: UploadFile | None = File(None),
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user)
):
	"""
	Обновляет базовые данные профиля: никнейм, почту и аватар.
	Валидатор Pydantic типа EmailStr проверяет формат почты до попадания в сервис.
	"""
	try:
		updated_user = await update_user_profile(
			session=session,
			target_user=user,
			data={"nickname": nickname, "email": email},
			avatar_file=avatar
		)

		return {"message": "Профиль успешно обновлен.", "avatar_url": updated_user.avatar_url}

	except ValueError as e:
		if "already exists" in str(e).lower():
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="Пользователь с таким адресом электронной почты уже существует."
			)
		raise
	except Exception as e:
		print(f"[PROFILE UPDATE ERROR] ID: {user.id}, Error: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Ошибка сервера при сохранении профиля."
		)

@router.post("/change-password", response_class=JSONResponse, status_code=status.HTTP_200_OK, operation_id="changeUserPassword")
async def api_change_password(
		# Используем схему Pydantic v2.x для строгой проверки тела запроса (application/json)
		data: ChangePasswordRequest,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user)
):
	"""
	Изменяет пароль текущей учетной записи.
	Валидация сложности пароля и минимальной длины выполняется схемой ChangePasswordRequest.
	"""
	success = await change_password(
		session=session,
		user=user,
		old_password=data.current_password,
		new_password=data.new_password
	)

	if not success:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Текущий пароль неверен. Операция отменена."
		)

	# Инвалидация всех активных сессий после смены пароля (Security best practice)
	new_session_token = secrets.token_urlsafe(64)
	stmt = (
		update(User)
		.where(User.id == user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	return {
		"message": "Пароль успешно изменен в целях безопасности.",
		"security_note": "Все ваши активные сессии на других устройствах были завершены.",
		"redirect_url": "/auth/login"
	}