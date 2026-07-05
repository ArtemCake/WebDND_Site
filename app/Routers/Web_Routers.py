# app/Routers/Web_Routers.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, APIRouter, Request, asyncio, Markup, markdown,
                            Depends, HTTPException, RedirectResponse, status, HTMLResponse)
from app.core.dependencies import get_current_user, OverloadedForm
from app.database.session import get_async_db
from app.core.security import create_access_token
from app.services.user_service import UserService
from app.database.models import User


# Создаем "подписыватель" (signer) для данных.
secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)

web_router = APIRouter()

# --- 1. ГЛАВНАЯ СТРАНИЦА И ПЕРЕНАПРАВЛЕНИЯ ---
@web_router.get("/")
async def root(request: Request):
	"""
	Главная страница. Редирект на профиль или логин.
	"""
	page_data = {
		"title": "D&D Мастерская",          # Для тега <title>
		"welcome_message": "Добро пожаловать в Личный Кабинет!", # Приветствие
		"description": (
			"Здесь вы сможете создавать миры, вести игры, "
			"хранить лор и управлять персонажами."
		),
		"features": [
			"Хранение лора миров",
			"Создание карточек персонажей",
			"Инструменты для Мастера"
		]
	}
	templates = request.app.state.templates
	response = templates.TemplateResponse(
	request=request,
	name="index.html",
	context={"context": page_data}
	)
	return response

# --- 2. РЕГИСТРАЦИЯ (ВЕБ-ФОРМА) ---
@web_router.get("/register")
async def register_page(request: Request):
	"""Страница с формой регистрации."""
	try:
		templates = request.app.state.templates
		response = templates.TemplateResponse(
			request=request,
			name="register.html",
			context={"username_value": ""}
		)
		return response
	except Exception as e:
		raise HTTPException(status_code=500, detail="Ошибка загрузки формы регистрации")

@web_router.post("/register")
async def register_user(request: Request,
                        username: str = OverloadedForm(...),
                        password: str = OverloadedForm(...)):
	# Теперь функция работает с 'templates', который пришел извне.
	db_manager = get_async_db()
	async with (db_manager as db):
		success, message = await UserService.register_new_user(db, username, password)
		if success:
			# 2. Если успех - редиректим (как раньше)
			return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
		else:
			# 3. Если ошибка - рендерим шаблон с ошибкой (как раньше)
			templates = request.app.state.templates
			return templates.TemplateResponse(
				request=request,
				name="register.html",
				context={"error": message,
				         "username_value": username}
			)

# --- 3. ВХОД (ВЕБ-ФОРМА) ---
@web_router.get("/login")
async def login_page(request: Request):
	"""Страница с формой входа."""
	try:
		templates = request.app.state.templates
		response = templates.TemplateResponse(
			request=request,
			name="login.html",
			context={"username_value": ""}
		)
		return response
	except Exception as e:
		raise HTTPException(status_code=500, detail="Ошибка загрузки формы входа")

@web_router.post("/login")
async def login(request: Request,
                username: str = OverloadedForm(...),
                password: str = OverloadedForm(...)):
	"""Обработчик входа в систему через веб-форму."""
	db_manager = get_async_db()
	async with (db_manager as db):
		success, message, user  = await UserService.web_login(db, username, password)
		# 2. Проверка логина и пароля
		if success:
			access_token = create_access_token(data={"sub": str(user.id)})
			# --- НОВОЕ: Создаем RedirectResponse ---
			next_url = "/users/me" # Куда перенаправить
			response = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
			# 1. Устанавливаем основной токен доступа
			response.set_cookie(
				key="access_token",
				value=f"Bearer {access_token}",
				httponly=True,
				max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
				samesite="none",
				secure=True
			)
			# 2. Устанавливаем ПОДПИСАННУЮ куку с user_id
			# Это безопасно, так как данные подписаны секретным ключом сервера.
			signed_user_id = serializer.dumps(user.id)
			response.set_cookie(
				key="temp_user_id",
				value=signed_user_id,
				max_age=60, # Живет только 1 минуту (на время редиректа)
				secure=True,
				samesite="none"
			)
			return response
		else:
			# Если ошибка — возвращаем страницу входа с текстом ошибки
			templates = request.app.state.templates
			return templates.TemplateResponse(
				request=request,
				name="login.html",
				context={"error": message,
				         "username_value": username}
			)

@web_router.post("/users/me/delete", include_in_schema=False)
@web_router.delete("/users/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_own_account(request: Request,
                             user: User = Depends(get_current_user)):
	if not user or not hasattr(user, 'id'):
		return RedirectResponse(url="/login")
	if hasattr(request.app.state, 'trackers') and user.id in request.app.state.trackers:
		data = request.app.state.trackers[user.id]
		tracker_instance = data['tracker']
		start_task = data['start_task']
		# 1. Останавливаем сам трекер
		await tracker_instance.stop()
		# 2. Отменяем задачу (на случай, если она зависла)
		if not start_task.done():
			start_task.cancel()
			try:
				await start_task
			except asyncio.CancelledError:
				pass # Ошибка отмены задачи — это нормально
		# 3. Удаляем трекер из словаря состояния
		del request.app.state.trackers[user.id]

	db_manager = get_async_db()
	async with (db_manager as db):
		success, message  = await UserService.web_delete_user(db, user)
		if success:
			response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
			response.set_cookie(
				key="session_id",
				value="",
				max_age=0,  # немедленно истекает
				expires="Thu, 01 Jan 1970 00:00:00 GMT",  # эпоха Unix
				path="/",
				httponly=True,
				secure=True,  # только HTTPS
				samesite="Strict"
			)
			response.delete_cookie("access_token")
			response.delete_cookie("temp_user_id")
			return response
		else:
			templates = request.app.state.templates
			return templates.TemplateResponse(
				request=request,
				name="profile.html",
				context={"user": user, "error": message}
			)

def get_document_content(request: Request, filename: str) -> str:
	"""
	Читает .md файл из папки static/docs и возвращает его содержимое.
	Если файл не найден, возвращает пустую строку или ошибку.
	"""
	project_root = request.app.state.project_root
	file_path = os.path.join(project_root, 'static', 'docs', filename)

	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			return f.read()
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Документ не найден")


@web_router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
	"""
	Отображает страницу Политики конфиденциальности.
	"""
	content = get_document_content(request, 'privacy_policy.md')
	# Конвертируем Markdown в HTML
	html_content = Markup(markdown.markdown(content))
	templates = request.app.state.templates
	return templates.TemplateResponse(
		request=request,
		name="document.html",
		context= {"title": "ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ И УСЛОВИЯ ИСПОЛЬЗОВАНИЯ",
		          "content": html_content}
	)

@web_router.get("/terms", response_class=HTMLResponse)
async def terms_of_service(request: Request):
	"""
	Отображает страницу Пользовательского соглашения.
	"""
	content = get_document_content(request, 'terms_of_service.md')
	# Конвертируем Markdown в HTML
	html_content = Markup(markdown.markdown(content))
	templates = request.app.state.templates
	return templates.TemplateResponse(
		request=request,
		name="document.html",
		context= {"title": "Политика конфиденциальности",
		          "content": html_content}
	)

