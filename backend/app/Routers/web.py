# backend/app/Routers/web.py

from Config.Config import settings
from Config.imports import (HTMLResponse, os, URLSafeTimedSerializer, Path,
                            Environment, FileSystemLoader, select_autoescape, Jinja2Templates,
						asyncio, Request, APIRouter, Depends, HTMLResponse, status, RedirectResponse)


# Создаем "подписыватель" (signer) для данных.
secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)

router = APIRouter()

# Определяем путь к папке с шаблонами относительно корня проекта
templates_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory="frontend/templates")
env_lock = asyncio.Lock()

@router.get("/", response_class=HTMLResponse, name="main_page_get")
async def get_main_page(request: Request):
	# Главная страница может сразу редиректить в лобби или показывать заглушку
	return """
    <!DOCTYPE html>
    <html lang="ru">
    <head><meta charset="UTF-8"><title>WebDND</title></head>
    <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
        <h1>D&D Онлайн стол</h1>
        <p>API работает.</p>
        <a href="/auth/login">Войти</a> | <a href="/auth/register">Регистрация</a>
    </body>
    </html>
    """

@router.get("/login", response_class=HTMLResponse, name="login_page_get")
async def get_login_page(request: Request):
	context = {"project_name": settings.PROJECT_NAME}
	# Здесь будет вызов templates.TemplateResponse после инициализации движка
	return templates.TemplateResponse(request, "login.html", context)

@router.get("/register", response_class=HTMLResponse, name="register_page_get")
async def get_register_page(request: Request):
	return templates.TemplateResponse(request, "register.html")

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard_page_get")
async def get_dashboard_page(request: Request):
	# Защищенная страница профиля/игр
	if not request.session.get("user_id"):
		return RedirectResponse(url="/auth/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

	context = {"request": request, "nickname": request.session.get("nickname")}
	return templates.TemplateResponse(request, "dashboard.html", context)