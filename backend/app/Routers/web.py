# backend/app/Routers/web.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, Path,
                        HTTPException, TemplateNotFound, Jinja2Templates,
						asyncio, Request, APIRouter, HTMLResponse, status, RedirectResponse)


router = APIRouter()

secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)

# Корректное определение пути относительно корня проекта
templates_dir = Path(settings.BASE_DIR+"/frontend"+"/templates")
templates = Jinja2Templates(directory=str(templates_dir))
env_lock = asyncio.Lock()

@router.get("/", response_class=HTMLResponse, name="main_page_get")
async def get_main_page(request: Request):
	"""
	Главная заглушка сайта.
	"""

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
async def get_login_page(request: Request):
	"""
	Страница входа.
	Если пользователь уже авторизован — перенаправляем в лобби.
	"""
	if request.session.get("user_id"):
		return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

	context = {
		"project_name": settings.PROJECT_NAME
	}

	try:
		return templates.TemplateResponse( request=request, name="login.html", context=context)
	except TemplateNotFound as e:
		raise HTTPException(status_code=404, detail="Страница login.html не найдена")

@router.get("/register", response_class=HTMLResponse, name="register_page_get")
async def get_register_page(request: Request):
	"""
	Страница регистрации.
	Если пользователь уже авторизован — перенаправляем в лобби.
	"""
	if request.session.get("user_id"):
		return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

	try:
		return templates.TemplateResponse(request=request,  name="register.html")
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница register.html не найдена")

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard_page_get")
async def get_dashboard_page(request: Request):
	"""
	Личный кабинет игрока.
	Защищенный роутер: проверяет наличие user_id в сессии.
	"""
	if not request.session.get("user_id"):
		return RedirectResponse(url="/auth/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

	context = {
		"nickname": request.session.get("nickname"),
		"project_name": settings.PROJECT_NAME
	}

	async with env_lock:
		try:
			return templates.TemplateResponse(request=request, name="dashboard.html", context=context)
		except TemplateNotFound:
			raise HTTPException(status_code=404, detail="Шаблон dashboard.html не найден")