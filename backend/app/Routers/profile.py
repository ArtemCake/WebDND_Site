# backend/app/Routers/profile.py

from backend.app.database.database import get_async_session
from Config.Config import settings
from Config.imports import (JSONResponse, HTMLResponse, APIRouter, Depends, HTTPException,
                            status, UploadFile, File, Request, EmailStr, BaseModel, Field, AsyncSession, UUID,
                            Form, CsrfProtect)
from backend.app.database.models.core.user import User
from backend.app.Services.user_service import (update_user_profile, change_password, get_current_user)


router = APIRouter(
	prefix="/profile",
	tags=["profile"],
)

class ProfileSettingsDTO(BaseModel):
	theme_color: str | None = Field(default="#a855f7", description="Основной цвет темы")
	background_url: str | None = Field(default=None, description="Ссылка на фоновое изображение")

class ProfileResponseDTO(BaseModel):
	id: UUID
	nickname: str
	email: EmailStr
	avatar_url: str | None = None
	is_email_verified: bool
	profile_settings: ProfileSettingsDTO

@router.get("/", response_class=HTMLResponse, name="profile_page_get")
async def get_profile_page(request: Request, user: User = Depends(get_current_user), csrf_protect: CsrfProtect = Depends()):
	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {
		"user": user,
		"project_name": settings.PROJECT_NAME,
		"csrf_token": csrf_token
	}
	templates = request.app.state.templates
	response = templates.TemplateResponse(request, "profile.html", context)
	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.get("/data", response_model=ProfileResponseDTO, operation_id="getCurrentUserProfile")
async def get_profile_data(user: User = Depends(get_current_user)):
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
		request: Request,
		nickname: str = Form(...),
		email: EmailStr = Form(...),
		avatar: UploadFile | None = File(None),
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
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
		request: Request,
		current_password: str = Form(...),
		new_password: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		user: User = Depends(get_current_user),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
	success = await change_password(
		session=session,
		user=user,
		old_password=current_password,
		new_password=new_password
	)

	if not success:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Текущий пароль неверен. Операция отменена."
		)

	return {
		"message": "Пароль успешно изменён!",
		"security_note": "На всякий случай мы завершили ваши сессии на других устройствах — просто войдите снова с новым паролем.",
		"redirect_url": "/login"
	}