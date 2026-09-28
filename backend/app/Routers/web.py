# backend/app/Routers/web.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, HTTPException, TemplateNotFound,
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
async def get_login_page(request: Request, user: User | None = Depends(get_optional_user)):
	"""
	Страница входа.
	Если пользователь уже авторизован — перенаправляем в лобби.

	ФИКС: раньше проверялось request.session.get("user_id"), но /auth/login
	никогда не пишет ничего в request.session — авторизация там идёт через
	JWT в cookie. Из-за этого уже вошедший пользователь всё равно видел
	страницу логина. Теперь статус проверяется тем же механизмом (cookie),
	что и в api.py.
	"""
	if user:
		return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

	context = {
		"project_name": settings.PROJECT_NAME
	}
	templates = request.app.state.templates
	try:
		return templates.TemplateResponse( request=request, name="login.html", context=context)
	except TemplateNotFound as e:
		raise HTTPException(status_code=404, detail="Страница login.html не найдена")

@router.get("/register", response_class=HTMLResponse, name="register_page_get")
async def get_register_page(request: Request, user: User | None = Depends(get_optional_user)):
	"""
	Страница регистрации.
	Если пользователь уже авторизован — перенаправляем в лобби.
	"""
	if user:
		return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
	templates = request.app.state.templates
	try:
		return templates.TemplateResponse(request=request,  name="register.html")
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница register.html не найдена")

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard_page_get")
async def get_dashboard_page(request: Request, user: User | None = Depends(get_optional_user)):
	"""
	Личный кабинет игрока.
	Защищенный роутер: проверяет наличие авторизации через JWT-cookie.

	ФИКС: раньше проверка шла по request.session.get("user_id"), которое
	не заполняется процессом логина из api.py — реальный авторизованный
	пользователь всё равно бесконечно редиректился на /auth/login.
	Теперь используется get_optional_user (тот же JWT-cookie, что и в API),
	а никнейм берётся из объекта пользователя, а не из сессии.
	"""
	if not user:
		return RedirectResponse(url="/auth/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

	context = {
		"nickname": user.nickname,
		"project_name": settings.PROJECT_NAME
	}

	async with env_lock:
		templates = request.app.state.templates
		try:
			return templates.TemplateResponse(request=request, name="dashboard.html", context=context)
		except TemplateNotFound:
			raise HTTPException(status_code=404, detail="Шаблон dashboard.html не найден")