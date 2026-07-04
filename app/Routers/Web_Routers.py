# app/Routers/Web_Routers.py

from Config.Config import settings
from Config.imports import (os, URLSafeTimedSerializer, APIRouter, Request)


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
