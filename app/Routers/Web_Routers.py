# app/Routers/Web_Routers.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, APIRouter, Request, select, Markup, markdown,
                            Depends, HTTPException, RedirectResponse, status, HTMLResponse)
from app.core.dependencies import get_current_user, OverloadedForm
from app.database.models.user_models import UserLog, AppLog
from app.database.session import get_async_db
from app.core.security import create_access_token
from app.repositories.srd_repository import SRDRepository
from app.schemas.spell_schema import SpellCreate, SpellUpdate
from app.services.srd_service import SRDService
from app.services.user_service import UserService
from app.database._models import User


# Создаем "подписыватель" (signer) для данных.
secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)

web_router = APIRouter()

# --- 1. ГЛАВНАЯ СТРАНИЦА И ПЕРЕНАПРАВЛЕНИЯ ---
@web_router.get("/")
async def home_page(request: Request, user: User = Depends(get_current_user)):
	"""
	Главная страница. Редирект на профиль или логин.
	"""
	templates = request.app.state.templates
	response = templates.TemplateResponse(
	request=request,
	name="index.html",
	context={"user_role": user.role.value if user and hasattr(user, 'role') else 'player',
	         "user": user}
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
			name="auth/register.html",
			context={"username_value": ""}
		)
		return response
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы регистрации: {e}")

@web_router.post("/register")
async def register_user(request: Request,
                        username: str = OverloadedForm(...),
                        role: str = OverloadedForm(...),
                        password: str = OverloadedForm(...)):
	# Теперь функция работает с 'templates', который пришел извне.
	db_manager = get_async_db()
	async with (db_manager as db):
		success, message = await UserService.register_new_user(db, username, password, role)
		if success:
			# 2. Если успех - редиректим (как раньше)
			return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
		else:
			# 3. Если ошибка - рендерим шаблон с ошибкой (как раньше)
			templates = request.app.state.templates
			return templates.TemplateResponse(
				request=request,
				name="auth/register.html",
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
			name="auth/login.html",
			context={"username_value": ""}
		)
		return response
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы входа: {e}")

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
			next_url = "/" # Куда перенаправить
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
				name="auth/login.html",
				context={"error": message,
				         "username_value": username}
			)

@web_router.post("/users/me/delete", include_in_schema=False)
@web_router.delete("/users/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_own_account(request: Request, user: User = Depends(get_current_user)):
	if not user or not hasattr(user, 'id'):
		return RedirectResponse(url="/login")
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
				samesite="strict"
			)
			response.delete_cookie("access_token")
			response.delete_cookie("temp_user_id")
			return response
		else:
			templates = request.app.state.templates
			return templates.TemplateResponse(
				request=request,
				name="profile.html",
				context={"user_role": user.role.value if user and hasattr(user, 'role') else 'player',
				         "user": user,
				         "error": message}
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

@web_router.get("/login?logout=1") # Использование query param для GET-запроса выхода
async def logout():
	"""
	Обработчик выхода из аккаунта.
	Удаляет токен из куки и перенаправляет на страницу авторизации.
	"""
	response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
	response.set_cookie(
		key="session_id",
		value="",
		max_age=0,  # немедленно истекает
		expires="Thu, 01 Jan 1970 00:00:00 GMT",  # эпоха Unix
		path="/",
		httponly=True,
		secure=True,  # только HTTPS
		samesite="strict"
	)
	response.delete_cookie("access_token")
	response.delete_cookie("temp_user_id")
	return response

#Роутеры меню

# ==============================================================================
# === СПРАВОЧНИК ЗАКЛИНАНИЙ (CRUD + List) ======================================
# ==============================================================================

@web_router.get("/core/spells", response_class=HTMLResponse, name="core.spells")
async def spells_list(
		request: Request,
		user: User = Depends(get_current_user),
		search_query: str = "",
		level: int = None
):
	"""Отображение страницы со списком всех заклинаний."""
	db_manager = get_async_db()
	async with (db_manager as db):
		spells = await SRDService.get_spells_list(db, search_query=search_query, level=level)
		templates = request.app.state.templates
		return templates.TemplateResponse(
			request=request,
			name="core/spells/list.html",
			context={
				"title": "Заклинания",
				"spells": spells,
				"user_role": user.role.value if user and hasattr(user, 'role') else 'player',
				"user": user,
				"current_search": search_query,
				"current_level": level
			}
		)

# --- ДЕТАЛЬНАЯ СТРАНИЦА (READ) ---
@web_router.get("/core/spells/{spell_id}", response_class=HTMLResponse, name="core.spells.detail")
async def spell_detail(
		request: Request,
		user: User = Depends(get_current_user),
		spell_id: int = None
):
	"""Страница с подробным описанием одного заклинания."""
	if not spell_id:
		raise HTTPException(status_code=404)

	db_manager = get_async_db()
	async with (db_manager as db):
		spell = await SRDService.get_spell_by_id(db, spell_id)

		if not spell:
			raise HTTPException(status_code=404, detail="Заклинание не найдено")
		templates = request.app.state.templates
		return templates.TemplateResponse(
			request=request,
			name="core/spells/detail.html",
			context={"title": spell.name,
			         "spell": spell,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)

# --- СОЗДАНИЕ (CREATE) ---
@web_router.get("/core/spells/create", response_class=HTMLResponse, name="core.spells.create")
async def spell_create_form(request: Request, user: User = Depends(get_current_user)):
	"""Отображает пустую форму создания нового заклинания."""
	if user.role.value != 'master':
		raise HTTPException(status_code=403, detail="Доступ запрещен")
	templates = request.app.state.templates
	return templates.TemplateResponse(
		request=request,
		name="core/spells/form.html",
		context={"title": "Новое заклинание",
		         "spell": None,
		         "error": None,
		         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
		         "user": user}
	)

@web_router.post("/core/spells/", name="core.spells.store")
async def spell_store(
		request: Request,
		payload: SpellCreate,
		user: User = Depends(get_current_user)
):
	"""Обрабатывает POST-запрос на создание заклинания."""
	if user.role.value != 'master':
		raise HTTPException(status_code=403)

	db_manager = get_async_db()
	async with (db_manager as db):
		success, message, obj = await SRDService.create_spell(db, payload)

		# Если запрос пришел от HTMX (наш фильтр или форма), возвращаем кусок HTML
		if "HX-Request" in request.headers:
			spells = await SRDService.get_spells_list(db)
			templates = request.app.state.templates

			if success:
				# При успехе обновляем сетку карточек
				return templates.TemplateResponse(
					request=request,
					name="core/spells/list.html",
					context={"spells": spells,
					         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
					         "user": user}
				)
			else:
				# При ошибке возвращаем форму с текстом ошибки
				return templates.TemplateResponse(
					request=request,
					name="core/spells/form.html",
					context={"title": "Ошибка создания",
					         "error": message,
					         "spell_data": payload,
					         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
					         "user": user},
					status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
				)

		# Обычный веб-запрос (не HTMX) - делаем редирект
		if success:
			return RedirectResponse(url="/core/spells", status_code=status.HTTP_303_SEE_OTHER)
		else:
			# В случае системной ошибки при обычном запросе можно вернуть на форму
			return RedirectResponse(url="/core/spells/create", status_code=status.HTTP_303_SEE_OTHER)

# --- РЕДАКТИРОВАНИЕ (UPDATE) ---
@web_router.get("/core/spells/{spell_id}/edit", response_class=HTMLResponse, name="core.spells.edit")
async def spell_edit_form(
		request: Request,
		user: User = Depends(get_current_user),
		spell_id: int = None
):
	"""Отображает форму редактирования с заполненными данными."""
	if user.role.value != 'master' or not spell_id:
		raise HTTPException(status_code=403)

	db_manager = get_async_db()
	async with (db_manager as db):
		spell = await SRDService.get_spell_by_id(db, spell_id)
		if not spell:
			raise HTTPException(status_code=404)

		templates = request.app.state.templates
		return templates.TemplateResponse(
			request=request,
			name="core/spells/form.html",
			context={"title": f"Редактировать: {spell.name}",
			         "spell": spell,
			         "error": None,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)

@web_router.put("/core/spells/{spell_id}", name="core.spells.update") # Используем PUT/PATCH
async def spell_update(
		request: Request,
		spell_id: int,
		payload: SpellUpdate,
		user: User = Depends(get_current_user)
):
	"""Обработка сохранения изменений."""
	if user.role.value != 'master':
		raise HTTPException(status_code=403)

	db_manager = get_async_db()
	async with (db_manager as db):
		# Сначала получаем объект из БД
		db_obj = await SRDService.get_spell_by_id(db, spell_id)
		if not db_obj:
			raise HTTPException(status_code=404)

		success, message, _ = await SRDService.update_spell(db, db_obj, payload)

		if "HX-Request" in request.headers:
			spells = await SRDService.get_spells_list(db)
			templates = request.app.state.templates

			if success:
				return templates.TemplateResponse(
					request=request,
					name="core/spells/_list_partial.html",
					context={"spells": spells,
					         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
					         "user": user},
					headers={"HX-Trigger": "closeModal"} # Можно закрыть модалку
				)
			else:
				return templates.TemplateResponse(
					request=request,
					name="core/spells/form.html",
					context={"title": "Ошибка",
					         "error": message,
					         "spell": db_obj,
					         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
					         "user": user},
					status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
				)

		return RedirectResponse(url=f"/core/spells/{spell_id}", status_code=status.HTTP_303_SEE_OTHER)

# --- УДАЛЕНИЕ (DELETE) ---
@web_router.delete("/core/spells/{spell_id}", name="core.spells.destroy")
async def spell_delete(
		request: Request,
		spell_id: int,
		user: User = Depends(get_current_user)
):
	"""Удаление заклинания (HTMX)."""
	if user.role.value != 'master':
		raise HTTPException(status_code=403)

	db_manager = get_async_db()
	async with (db_manager as db):
		db_obj = await SRDService.get_spell_by_id(db, spell_id)
		if db_obj:
			await SRDService.delete_spell(db, db_obj)

		# После удаления всегда возвращаем обновленный список
		spells = await SRDService.get_spells_list(db)
		templates = request.app.state.templates
		return templates.TemplateResponse(
			request=request,
			name="core/spells/list.html",
			context={"spells": spells,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)

@web_router.get("/core/items", response_class=HTMLResponse, name="core.items")
async def items_list(request: Request,
                     user: User = Depends(get_current_user)):
	templates = request.app.state.templates
	q = request.query_params.get("q", "")

	type_param = request.query_params.get("type")

	db_manager = get_async_db()
	async with (db_manager as db):
		items = await SRDService.get_items_list(
			db,
			search_query=q,
			item_type=str(type_param)
		)

		return templates.TemplateResponse(
			request=request,
			name="core/items/list.html",
			context={"title": "Предметы",
			         "items": items,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)

@web_router.get("/core/items/{item_id}", response_class=HTMLResponse, name="core.item_detail")
async def item_detail(request: Request, user: User = Depends(get_current_user), item_id: int = None):
	"""Детальная страница заклинания."""
	if not item_id:
		raise HTTPException(status_code=404)

	templates = request.app.state.templates

	db_manager = get_async_db()
	async with (db_manager as db):
		# Используем метод сервиса для поиска по ID
		item = await SRDRepository.get_item_by_id(db, item_id)

		if not item:
			raise HTTPException(status_code=404, detail="Предмет не найден")

		return templates.TemplateResponse(
			request=request,
			name="core/items/detail.html",
			context={
				"title": item.name,
				"item": item,
				"user_role": user.role.value if user and hasattr(user, 'role') else 'player',
				"user": user}
		)

@web_router.get("/core/bestiary", response_class=HTMLResponse, name="core.bestiary")
async def bestiary_list(request: Request,
                        user: User = Depends(get_current_user)):
	templates = request.app.state.templates
	q = request.query_params.get("q", "")

	cr_param = request.query_params.get("cr")
	creature_type_param = request.query_params.get("type")

	db_manager = get_async_db()
	async with (db_manager as db):
		bestiarys = await SRDService.get_bestiary_list(
			db,
			search_query=q,
			cr=str(cr_param),
			creature_type=str(creature_type_param)
		)

		return templates.TemplateResponse(
			request=request,
			name="core/bestiary/list.html",
			context={"title": "Монстры",
			         "monsters": bestiarys,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)

@web_router.get("/core/bestiary/{bestiary_id}", response_class=HTMLResponse, name="core.bestiary_detail")
async def bestiary_detail(request: Request, user: User = Depends(get_current_user), bestiary_id: int = None):
	"""Детальная страница заклинания."""
	if not bestiary_id:
		raise HTTPException(status_code=404)

	templates = request.app.state.templates

	db_manager = get_async_db()
	async with (db_manager as db):
		# Используем метод сервиса для поиска по ID
		bestiary = await SRDRepository.get_monster_by_id(db, bestiary_id)

		if not bestiary:
			raise HTTPException(status_code=404, detail="Монстр не найден")

		return templates.TemplateResponse(
			request=request,
			name="core/bestiary/detail.html",
			context={
				"title": bestiary.name,
				"bestiary": bestiary,
				"user_role": user.role.value if user and hasattr(user, 'role') else 'player',
				"user": user}
		)

@web_router.get("/lore", response_class=HTMLResponse, name="lore.index")
async def lore_page(request: Request):
	return _render_section_page(request, "Лор и история")

@web_router.get("/campaign/dashboard", response_class=HTMLResponse, name="campaign.dashboard")
async def campaign_dashboard(request: Request):
	return _render_section_page(request, "Панель кампаний")

@web_router.get("/campaign/npcs", response_class=HTMLResponse, name="campaign.npcs")
async def npcs_journal(request: Request):
	return _render_section_page(request, "Журнал НПС")

@web_router.get("/vtt/board", response_class=HTMLResponse, name="vtt.board")
async def vtt_board(request: Request):
	return _render_section_page(request, "Виртуальный стол")

@web_router.get("/vtt/initiative", response_class=HTMLResponse, name="vtt.initiative")
async def initiative_tracker(request: Request):
	return _render_section_page(request, "Трекер инициативы")

@web_router.get("/profile/characters", response_class=HTMLResponse, name="profile.characters")
async def characters_list(request: Request):
	"""Страница со списком персонажей пользователя."""
	return _render_section_page(request, "Мои персонажи")

@web_router.get("/profile/inventory", response_class=HTMLResponse, name="profile.inventory")
async def inventory_view(request: Request):
	"""Инвентарь выбранного персонажа."""
	return _render_section_page(request, "Инвентарь")

@web_router.get("/profile/settings", response_class=HTMLResponse, name="profile.settings")
async def settings_page(request: Request):
	"""Настройки аккаунта."""
	return _render_section_page(request, "Настройки")

# Универсальная функция-заглушка
def _render_section_page(request: Request, title: str):
	templates = request.app.state.templates
	return templates.TemplateResponse(
		request=request,
		name="section_stub.html",
		context={"title": title}
	)

# --- ГРУППА АДМИНСКИХ РОУТЕРОВ ---
@web_router.get("/admin/user-logs", response_class=HTMLResponse, name="admin.user_logs")
async def admin_user_logs(request: Request, user: User = Depends(get_current_user)):
	"""Просмотр журнала действий пользователей."""
	if user.role.value != 'admin':
		raise HTTPException(status_code=403, detail="Доступ запрещен")

	templates = request.app.state.templates

	db_manager = get_async_db()
	async with (db_manager as db):
		# Получаем последние 500 записей, сортируем по дате убывания
		result = await db.execute(select(UserLog).order_by(UserLog.timestamp.desc()).limit(500))
		logs = result.scalars().all()

		return templates.TemplateResponse(
			request=request,
			name="admin/user_logs.html",
			context={"title": "Логи пользователей",
			         "logs": logs,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)

@web_router.get("/admin/app-logs", response_class=HTMLResponse, name="admin.app_logs")
async def admin_app_logs(request: Request, user: User = Depends(get_current_user)):
	"""Просмотр системного журнала приложения (ошибки БД, стартапы)."""
	if user.role.value != 'admin':
		raise HTTPException(status_code=403, detail="Доступ запрещен")

	templates = request.app.state.templates

	db_manager = get_async_db()
	async with (db_manager as db):
		result = await db.execute(select(AppLog).order_by(AppLog.timestamp.desc()).limit(500))
		logs = result.scalars().all()

		return templates.TemplateResponse(
			request=request,
			name="admin/app_logs.html",
			context={"title": "Системные логи",
			         "logs": logs,
			         "user_role": user.role.value if user and hasattr(user, 'role') else 'player',
			         "user": user}
		)