# main.py

from Config.imports import (FastAPI, asynccontextmanager, asyncio, CORSMiddleware,
                                 StaticFiles, Jinja2Templates, base64, RequestValidationError, Request,
                                 JSONResponse, HTMLResponse, Depends, uvicorn, APIRoute, os, pathlib)
from Config.Config import settings
from app.database.session import get_async_db, get_async_session_factory
from app.database.database import engine, metadata
import app.Routers.main as api_module
import app.Routers.Web_Routers as web_module # Модуль с Веб роутерами
from alembic.command import upgrade
from alembic.config import Config


async def apply_migrations():
	try:
		alembic_cfg = Config("alembic.ini")
		alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))
		upgrade(alembic_cfg, "head")
	except Exception as e:
		raise

@asynccontextmanager
async def lifespan(app: FastAPI):

	async with engine.begin() as conn:
		await conn.run_sync(metadata.create_all)
	# Создание глобальной сессии (фабрики)
	async_session = get_async_db()
	app.state.async_session = async_session
	session_factory = get_async_session_factory
	app.state.session_factory = session_factory
	# Запуск трекеров для активных пользователей
	app.state.settings = settings
	await asyncio.sleep(1)
	yield # Точка, где приложение начинает работать

def use_multipart_form_dep(dep):
	if hasattr(dep, "func"):
		for index, param in enumerate(dep.func.__annotations__.get("dependant", {}).get("params", [])):
			# Если параметр — это стандартная зависимость Form,
			# заменяем её на нашу OverloadedForm
			if param["type"] == "form" and param.get("default") is False:
				# Меняем тип зависимости
				param["__class__"] = "multipart_form"
	return dep

# --- СОЗДАНИЕ ПРИЛОЖЕНИЯ ---
app = FastAPI(
	title=settings.PROJECT_NAME,
	description=settings.DESCRIPTION,
	version=settings.VERSION,
	lifespan=lifespan,
)

class ProxyHeaderMiddleware:
	"""
	Промежуточное ПО для обработки прокси-заголовков.
	Учитывает возможность передачи списка значений через запятую.
	"""
	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		if scope["type"] != "http":
			await self.app(scope, receive, send)
			return

		headers = dict(scope["headers"])

		if b"x-forwarded-proto" in headers:
			# Получаем значение заголовка и декодируем из байтов
			proto_value = headers[b"x-forwarded-proto"].decode()

			# Разделяем строку по запятым (если их несколько) и берем первый элемент
			# .lower() делает проверку нечувствительной к регистру
			first_proto = proto_value.split(",")[0].strip().lower()

			if first_proto == "https":
				scope["scheme"] = "https"

		await self.app(scope, receive, send)

app.add_middleware(ProxyHeaderMiddleware)

# --- ПОДКЛЮЧЕНИЕ CORS И СТАТИКИ ---
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.BACKEND_CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
BASE_DIR = pathlib.Path(__file__).parent.resolve()
os.environ['PROJECT_ROOT'] = str(BASE_DIR)
app.state.templates = templates
app.state.project_root = BASE_DIR
# Получаем окружение Jinja2 из глобального объекта templates
env = templates.env

# Определяем функцию фильтра
def b64encode_filter(value):
	return base64.b64encode(value).decode('utf-8')

# Регистрируем фильтр в окружении
env.filters['b64encode'] = b64encode_filter

# Создаем зависимость, которая возвращает наш глобальный объект 'templates'
def get_templates():
	return templates

# --- ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ОШИБОК (Хорошая практика) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
	return JSONResponse(
		status_code=422,
		content={"detail": f"Некорректные данные в запросе. {exc}"},
	)

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
	return HTMLResponse(content="<h1>404 - Страница не найдена</h1>", status_code=404)

# --- ПОДКЛЮЧЕНИЕ МОДУЛЕЙ (ГЛАВНЫЙ ШАГ) ---

# 1. Подключаем API роуты с префиксом /api/v1/auth...
app.include_router(api_module.router, prefix=settings.API_V1_STR)

# 2. Подключаем Веб роуты (страницы HTML)
app.include_router(
	web_module.web_router,
	dependencies=[Depends(get_templates)] # Передаем саму функцию, а не ее вызов
)

# Применяем эту функцию ко всем роутерам приложения
for route in app.router.routes:
	if isinstance(route, APIRoute):
		route.dependant = use_multipart_form_dep(route.dependant)


if __name__ == "__main__":
	asyncio.run(apply_migrations())
	uvicorn.run(
		"main:app",
		host="127.0.0.1",
		port=8080,
		log_level="info",
		reload=True
	)