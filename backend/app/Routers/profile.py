# backend/app/Routers/profile.py

from backend.app.database.database import get_async_session
from backend.app.Services.security_service import oauth2_scheme
from backend.app.Services.user_service import (update_user_profile, change_password, User, get_current_user)
from Config.Config import settings
from Config.imports import (JSONResponse, HTMLResponse, APIRouter, Depends, HTTPException,
                            status, UploadFile, File, Request, EmailStr, BaseModel, Field,
                            AsyncSession, UUID, Form, Path, Jinja2Templates, asyncio)


router = APIRouter(
	prefix="/profile",
	tags=["profile"],
	dependencies=[Depends(oauth2_scheme)]
)
# Определяем путь к папке с шаблонами относительно корня проекта
templates_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory="frontend/templates")
env_lock = asyncio.Lock()

# --- СХЕМЫ ЗАПРОСОВ И ОТВЕТОВ ---

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

class PasswordChangeDTO(BaseModel):
	"""Данные для смены пароля."""
	current_password: str = Field(..., min_length=8)
	new_password: str = Field(..., min_length=8)

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
	return templates.TemplateResponse(request, "profile.html", context)

@router.get("/data", response_model=ProfileResponseDTO, operation_id="getCurrentUserProfile")
async def get_profile_data(user: User = Depends(get_current_user)):
	"""
	Возвращает структурированные данные текущего пользователя для HTMX-загрузки формы.
	Используется при открытии страницы и динамическом обновлении данных без перезагрузки.
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
		nickname: str = Form(...),
		email: EmailStr = Form(...),
		avatar: UploadFile | None = File(None),
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user)
):
	"""
	Обновляет базовые данные профиля: никнейм, почту и аватар.

	- Raises:
		HTTPException 409: Если новый email занят другим пользователем.
		HTTPException 401: Если сессия недействительна.
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
		# Логируем непредвиденную ошибку перед пробросом
		print(f"[PROFILE UPDATE ERROR] ID: {user.id}, Error: {e}")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка сервера при сохранении профиля.")

@router.post("/change-password", response_class=JSONResponse, status_code=status.HTTP_200_OK, operation_id="changeUserPassword")
async def api_change_password(
		data: PasswordChangeDTO,
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user)
):
	"""
	Изменяет пароль текущей учетной записи.

	ВАЖНО: При успешном изменении сервис автоматически инвалирует все активные токены
	через обновление поля active_session_token в БД (согласно п. 38 ТЗ).
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

	return {
		"message": "Пароль успешно изменен в целях безопасности.",
		"security_note": "Все ваши активные сессии на других устройствах были завершены.",
		"redirect_url": "/auth/login"
	}