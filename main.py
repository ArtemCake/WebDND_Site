# main.py

from Config.imports import (FastAPI, Request, StaticFiles, Jinja2Templates, uvicorn, HTMLResponse, asyncio)
from app.database.database import engine, Base


# --- НОВЫЙ СПОСОБ ОБРАБОТКИ СОБЫТИЙ ---
async def lifespan(app: FastAPI):
	# КОД ПРИ СТАРТЕ СЕРВЕРА
	print("🚀 Запуск приложения... Инициализируем базу данных.")

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all) # Создаем таблицы

	print("✅ База данных готова!")

	yield # Точка разделения между стартом и остановкой

	# КОД ПРИ ОСТАНОВКЕ СЕРВЕРА
	print("🛑 Приложение останавливается...")
	# Здесь можно добавить логику для корректного закрытия трекеров или других задач
	await asyncio.sleep(1) # Даем время на завершение фоновых задач
	print("👋 До свидания!")

# Передаем функцию lifespan при создании объекта app
app = FastAPI(lifespan=lifespan, title="D&D Сайт", description="Инструментарий для Мастера")

# Подключаем статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
	print("Запускаем событие старта... Создаем таблицы в БД.")
	async with engine.begin() as conn:
		# Теперь metadata содержит информацию о классе Character!
		await conn.run_sync(Base.metadata.create_all)
	print("База данных готова!")

# --- Веб-маршруты (HTML страницы) ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
	return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
	asyncio.run(apply_migrations())
	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=8080,
		log_level="info",
		reload=True
	)