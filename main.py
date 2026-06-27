# main.py

from Config.imports import (FastAPI, Request, StaticFiles, Jinja2Templates, uvicorn, HTMLResponse)
from app.database.database import engine, Base
from app.models import Character # Импортируем нашу будущую модель

# Создаем приложение
app = FastAPI(title="D&D Сайт", description="Инструментарий для Мастера")

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
	print("Запуск сервера Uvicorn...")
	uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)