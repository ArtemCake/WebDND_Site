# backend/app/Routers/web.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, HTTPException, TemplateNotFound, CsrfProtect,
                            asyncio, Request, APIRouter, HTMLResponse, status, RedirectResponse, Depends)
from backend.app.Services.user_service import get_optional_user
from backend.app.database.models.core.user import User


router = APIRouter()

secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)
env_lock = asyncio.Lock()

@router.get("/", response_class=HTMLResponse, name="main_page_get")
async def get_main_page(request: Request):
	"""
	Главная заглушка сайта.
	"""
	templates = request.app.state.templates

	try:
		return templates.TemplateResponse(request=request,name="index.html")
	except TemplateNotFound:
		# Fallback-заглушка, если шаблон еще не создан
		return """
        <!DOCTYPE html>
        <html lang="ru">
        <head><meta charset="UTF-8"><title>WebDND</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>D&D Онлайн стол</h1>
            <p>Главная страница.</p>
            <a href="/login">Войти</a> | <a href="/register">Регистрация</a>
        </body>
        </html>
        """

@router.get("/login", response_class=HTMLResponse, name="login_page_get")
async def get_login_page(request: Request,
                         user: User | None = Depends(get_optional_user),
                         csrf_protect: CsrfProtect = Depends()
                         ):
	if user:
		return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {"project_name": settings.PROJECT_NAME, "csrf_token": csrf_token}
	templates = request.app.state.templates
	try:
		response = templates.TemplateResponse(request=request, name="login.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница login.html не найдена")

	csrf_protect.set_csrf_cookie(signed_token, response)
	return response

@router.get("/register", response_class=HTMLResponse, name="register_page_get")
async def get_register_page(request: Request,
                            user: User | None = Depends(get_optional_user),
                            csrf_protect: CsrfProtect = Depends()
                            ):
	"""
	Страница регистрации.
	Если пользователь уже авторизован — перенаправляем в лобби.
	"""
	if user:
		return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {"project_name": settings.PROJECT_NAME, "csrf_token": csrf_token}
	templates = request.app.state.templates

	try:
		return templates.TemplateResponse(request=request,  name="register.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница register.html не найдена")

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard_page_get")
async def get_dashboard_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	if not user:
		return RedirectResponse(url="/auth/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

	csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
	context = {
		"user": user,
		"nickname": user.nickname,
		"project_name": settings.PROJECT_NAME,
		"csrf_token": csrf_token
	}

	async with env_lock:
		templates = request.app.state.templates
		try:
			response = templates.TemplateResponse(request=request, name="dashboard.html", context=context)
		except TemplateNotFound:
			raise HTTPException(status_code=404, detail="Шаблон dashboard.html не найден")

	csrf_protect.set_csrf_cookie(signed_token, response)
	return response