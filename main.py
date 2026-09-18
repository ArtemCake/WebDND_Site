

from Config.Config import settings
from backend.app.database.database import engine, Base
import backend.app.Routers.api as api_module
import backend.app.Routers.web as web_module
import backend.app.Routers.profile as profile_module
from Config.imports import (FastAPI, asynccontextmanager, CORSMiddleware, Path, StaticFiles, Jinja2Templates,
	base64, RequestValidationError, Request, asyncio, JSONResponse, HTMLResponse, uvicorn,
	APIRoute, os, command, Config)
from starlette.middleware.sessions import SessionMiddleware
import backend.app.database._models


# --- ПУТЬ К КОНФИГУРАЦИИ ALEMBIC ---
BASE_DIR = Path(__file__).resolve().parent
ALEMBIC_CONFIG_PATH = str(BASE_DIR / "alembic.ini")
SCRIPT_LOCATION = str(BASE_DIR / "backend" / "db_migrations")

async def apply_migrations():
	"""
	Применяет миграции БД перед запуском сервера.
	ВАЖНО: Выполняется вне цикла событий FastAPI через run_in_executor,
	чтобы не блокировать асинхронный старт из-за синхронного Alembic.
	"""
	def _run_sync_migrations():
		try:
			print("[STARTUP] Применение миграций...")

			cfg = Config(ALEMBIC_CONFIG_PATH)
			cfg.set_main_option("script_location", SCRIPT_LOCATION)

			# Подставляем URL без драйвера asyncpg для совместимости с Alembic
			sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
			cfg.set_main_option("sqlalchemy.url", sync_url)

			command.upgrade(cfg, "head")
			print("[STARTUP] ✅ Миграции БД успешно применены")
		except Exception as e:
			print(f"[STARTUP][ERROR] Ошибка применения миграций: {e}")
			raise RuntimeError("База данных недоступна или миграции некорректны.") from e

	loop = asyncio.get_running_loop()
	await loop.run_in_executor(None, _run_sync_migrations)

@asynccontextmanager
async def lifespan(app: FastAPI):
	await apply_migrations()

	async with engine.begin() as conn:
		print("[STARTUP] Запущено создание таблиц БД")
		await conn.run_sync(Base.metadata.create_all)

	app.state.settings = settings
	print("[STARTUP] ✅ Таблицы БД успешно созданы")

	yield

	await engine.dispose()
	print("[SHUTDOWN] Соединения с БД закрыты.")

app = FastAPI(
	title=settings.PROJECT_NAME,
	description=settings.DESCRIPTION,
	version=settings.VERSION,
	lifespan=lifespan,
)

# --- MIDDLEWARE (ВАЖЕН ПОРЯДОК) ---

# 1. Proxy Header (для правильного определения HTTPS за прокси)
class ProxyHeaderMiddleware:
	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		if scope["type"] != "http":
			await self.app(scope, receive, send)
			return

		headers = dict(scope["headers"])
		if b"x-forwarded-proto" in headers:
			proto_value = headers[b"x-forwarded-proto"].decode()
			first_proto = proto_value.split(",")[0].strip().lower()
			if first_proto == "https":
				scope["scheme"] = "https"
		await self.app(scope, receive, send)

app.add_middleware(ProxyHeaderMiddleware)

# 2. Sessions (ДОЛЖЕН быть ДО CORS и роутов!)
# Решает ошибку 'SessionMiddleware must be installed to access request.session'
app.add_middleware(
	SessionMiddleware,
	secret_key=settings.SECRET_KEY,
	session_cookie="webdnd_session",
	max_age=604800, # 7 дней в секундах
	same_site="lax"
)

# 3. CORS (должен быть строго до регистрации роутеров)
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.BACKEND_CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)

# --- СТАТИЧЕСКИЕ ФАЙЛЫ И ШАБЛОНЫ ---
app.mount("/frontend/static", StaticFiles(directory=str(BASE_DIR / "frontend" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))
env = templates.env

def static_url(filename: str) -> str:
	return f"/frontend/static/{filename.lstrip('/')}"

def b64encode_filter(value):
	return base64.b64encode(value).decode('utf-8')

env.globals["static_url"] = static_url
env.filters['b64encode'] = b64encode_filter

# --- ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ОШИБОК ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
	return JSONResponse(status_code=422, content={"detail": f"Некорректные данные: {exc.errors()}"})

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
	return HTMLResponse(content="<h1>404 - Страница не найдена</h1>", status_code=404)

# --- ЗАВИСИМОСТЬ ДЛЯ MULTIPART FORM DATA (Fix HTMX + Pydantic) ---
def use_multipart_form_dep(dep):
	if hasattr(dep, "func"):
		for index, param in enumerate(dep.func.__annotations__.get("dependant", {}).get("params", [])):
			if param["type"] == "form" and param.get("default") is False:
				param["__class__"] = "multipart_form"
	return dep

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
os.environ['PROJECT_ROOT'] = str(BASE_DIR)
app.state.templates = templates
app.state.project_root = BASE_DIR

# --- ПОДКЛЮЧЕНИЕ РОУТЕРОВ ---
app.include_router(api_module.router)
app.include_router(web_module.router)
#app.include_router(profile_module.router)

# Применяем фиксы форм ко всем API-роутам
for route in app.router.routes:
	if isinstance(route, APIRoute):
		route.dependant = use_multipart_form_dep(route.dependant)

if __name__ == "__main__":
	uvicorn.run(
		"main:app",
		host="127.0.0.1",
		port=8080,
		log_level="info",
		reload=True
	)