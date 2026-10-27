# backend/app/Routers/web.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, HTTPException, TemplateNotFound, CsrfProtect,
                            Request, APIRouter, HTMLResponse, status, RedirectResponse, Depends, UUID)
from backend.app.Core.csrf import ensure_csrf_tokens, apply_csrf_tokens
from backend.app.Services.Core.user_service import get_optional_user
from backend.app.Database.Models.Core.user import User
from backend.app.Services.legal_service import render_legal_markdown


router = APIRouter()

secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)

@router.get("/", response_class=HTMLResponse, name="main_page_get")
async def get_main_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	"""
	Главная заглушка сайта.
	"""
	templates = request.app.state.templates
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {"user": user, "csrf_token": csrf_token}
	try:
		response = templates.TemplateResponse(request=request, name="index.html", context=context)
		apply_csrf_tokens(response, csrf_protect, csrf_page)
		return response
	except TemplateNotFound:
		# Fallback-заглушка, если шаблон еще не создан
		return """
        <!DOCTYPE html>
        <html lang="ru">
        <head><meta charset="UTF-8"><title>WorldLoom</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>D&D Онлайн стол</h1>
            <p>Главная страница.</p>
            <a href="/login">Войти</a> | <a href="/register">Регистрация</a>
        </body>
        </html>
        """

@router.get("/login", response_class=HTMLResponse, name="login_page_get")
async def get_login_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	if user:
		return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)

	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {"project_name": settings.PROJECT_NAME, "csrf_token": csrf_token}
	templates = request.app.state.templates
	try:
		response = templates.TemplateResponse(request=request, name="login.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница login.html не найдена")

	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/register", response_class=HTMLResponse, name="register_page_get")
async def get_register_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	"""
	Страница регистрации.
	Если пользователь уже авторизован — перенаправляем в лобби.
	"""
	if user:
		return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)

	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {"project_name": settings.PROJECT_NAME, "csrf_token": csrf_token}
	templates = request.app.state.templates

	try:
		response = templates.TemplateResponse(request=request, name="register.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница register.html не найдена")

	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/cookie-policy", response_class=HTMLResponse, name="cookie_policy_page_get")
async def get_cookie_policy_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	"""Статичная страница политики использования cookie."""
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {
	"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
	"legal_content": render_legal_markdown("cookie_policy.md")
	}
	templates = request.app.state.templates
	try:
		response = templates.TemplateResponse(request=request, name="docs/cookie_policy.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница cookie_policy.html не найдена")
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/terms", response_class=HTMLResponse, name="terms_page_get")
async def get_terms_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"legal_content": render_legal_markdown("terms_of_service.md")
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="docs/terms.html", context=context)
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/privacy-policy", response_class=HTMLResponse, name="privacy_policy_page_get")
async def get_privacy_policy_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {
		"user": user, "project_name": settings.PROJECT_NAME, "csrf_token": csrf_token,
		"legal_content": render_legal_markdown("privacy_policy.md")
	}
	response = request.app.state.templates.TemplateResponse(request=request, name="docs/privacy_policy.html", context=context)
	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard_page_get")
async def get_dashboard_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	if not user:
		return RedirectResponse(url="/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
	if not user.is_email_verified:
			return RedirectResponse(url="/profile?verify=required", status_code=status.HTTP_303_SEE_OTHER)

	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {
		"user": user,
		"nickname": user.nickname,
		"project_name": settings.PROJECT_NAME,
		"csrf_token": csrf_token
	}

	templates = request.app.state.templates
	try:
		response = templates.TemplateResponse(request=request, name="dashboard.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Шаблон dashboard.html не найден")

	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/forgot-password", response_class=HTMLResponse, name="forgot_password_page_get")
async def get_forgot_password_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	if user:
		return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)

	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {"project_name": settings.PROJECT_NAME, "csrf_token": csrf_token}
	templates = request.app.state.templates
	try:
		response = templates.TemplateResponse(request=request, name="forgot_password.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница forgot_password.html не найдена")

	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

@router.get("/reset-password", response_class=HTMLResponse, name="reset_password_page_get")
async def get_reset_password_page(request: Request, token: str = "", user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	if user:
		return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)

	csrf_page = ensure_csrf_tokens(request, csrf_protect)
	csrf_token = csrf_page.token
	context = {"project_name": settings.PROJECT_NAME, "csrf_token": csrf_token, "reset_token": token}
	templates = request.app.state.templates
	try:
		response = templates.TemplateResponse(request=request, name="reset_password.html", context=context)
	except TemplateNotFound:
		raise HTTPException(status_code=404, detail="Страница reset_password.html не найдена")

	apply_csrf_tokens(response, csrf_protect, csrf_page)
	return response

def _render_game_systems_page(request: Request, user: User | None, csrf_protect: CsrfProtect, page_mode: str, system_id: UUID | None = None):
	csrf_page = ensure_csrf_tokens(request, csrf_protect)

	response = request.app.state.templates.TemplateResponse(
		request=request,
		name="games/game_systems.html",
		context={
			"user": user,
			"project_name": settings.PROJECT_NAME,
			"csrf_token": csrf_page.token,
			"page_mode": page_mode,
			"system_id": str(system_id) if system_id else "",
		},
	)

	apply_csrf_tokens(response, csrf_protect, csrf_page)

	return response

@router.get("/game-systems/catalog", response_class=HTMLResponse, name="game_systems_catalog_get")
async def game_systems_catalog_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	return _render_game_systems_page(request, user, csrf_protect, "list")

# /new должен быть зарегистрирован раньше /{system_id}.
@router.get("/game-systems/catalog/new", response_class=HTMLResponse, name="game_systems_create_get")
async def game_systems_create_page(request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	return _render_game_systems_page(request, user, csrf_protect, "create")

@router.get("/game-systems/catalog/{system_id}/edit", response_class=HTMLResponse, name="game_systems_edit_get")
async def game_systems_edit_page(system_id: UUID, request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	return _render_game_systems_page(request, user, csrf_protect, "edit", system_id)

@router.get("/game-systems/catalog/{system_id}", response_class=HTMLResponse, name="game_systems_view_get")
async def game_systems_view_page(system_id: UUID, request: Request, user: User | None = Depends(get_optional_user), csrf_protect: CsrfProtect = Depends()):
	return _render_game_systems_page(request, user, csrf_protect, "view", system_id)