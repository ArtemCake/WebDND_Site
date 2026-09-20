# main.py

from Config.Config import settings
from backend.app.database.database import engine
import backend.app.Routers.api as api_module
import backend.app.Routers.web as web_module
import backend.app.Routers.profile as profile_module
from Config.logger import setup_logging
from Config.imports import (FastAPI, asynccontextmanager, CORSMiddleware, Path, StaticFiles, Jinja2Templates, SessionMiddleware,
                            base64, RequestValidationError, Request, asyncio, JSONResponse, HTMLResponse, uvicorn, os, command, Config)


# --- ПУТЬ К КОНФИГУРАЦИИ ALEMBIC ---
BASE_DIR = Path(settings.BASE_DIR)
ALEMBIC_CONFIG_PATH = str(BASE_DIR / "alembic.ini")
SCRIPT_LOCATION = str(BASE_DIR / "backend" / "db_migrations")

# --- ИНИЦИАЛИЗАЦИЯ ЛОГГЕРА ---
log = setup_logging(app_name="WebDND_Site")

async def apply_migrations():
	"""
	Применяет миграции БД перед запуском сервера.
	"""
	def _run_sync_migrations():
		try:
			log.info("[STARTUP][MIGRATIONS] Загрузка конфигурации Alembic...")

			if not Path(ALEMBIC_CONFIG_PATH).exists():
				raise FileNotFoundError(f"Файл alembic.ini не найден: {ALEMBIC_CONFIG_PATH}")
			if not Path(SCRIPT_LOCATION).exists():
				raise FileNotFoundError(f"Папка скриптов не найдена: {SCRIPT_LOCATION}")

			# Проверяем, есть ли хотя бы один файл миграции
			versions_dir = Path(SCRIPT_LOCATION) / "versions"
			if not versions_dir.exists() or not any(versions_dir.glob("*.py")):
				log.info("[STARTUP][MIGRATIONS] Папка versions пуста — миграции пропускаются.")
				return

			cfg = Config(ALEMBIC_CONFIG_PATH)
			cfg.set_main_option("script_location", SCRIPT_LOCATION)

			# Формируем URL для psycopg2 (синхронный режим)
			sync_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg", "postgresql")
			cfg.set_main_option("sqlalchemy.url", sync_url)

			log.info(f"[STARTUP][MIGRATIONS] Итоговый URL для Alembic: {sync_url}")
			log.info("[STARTUP][MIGRATIONS] Выполнение command.upgrade(head)...")

			command.upgrade(cfg, "head")
			log.info("[STARTUP][MIGRATIONS] ✅ Миграции успешно применены.")

		except Exception as e:
			log.critical(
				f"[STARTUP][FATAL MIGRATION ERROR] {type(e).__name__}: {e}",
				exc_info=True
			)
			raise

	# Освобождаем async-пул перед синхронной миграцией,
	# иначе asyncpg держит соединения и блокирует DDL
	await engine.dispose()

	loop = asyncio.get_running_loop()
	await loop.run_in_executor(None, _run_sync_migrations)

@asynccontextmanager
async def lifespan(app: FastAPI):
	try:
		log.info("[STARTUP] Начало инициализации...")

		if not os.path.exists(ALEMBIC_CONFIG_PATH):
			log.critical(f"[FATAL] Файл alembic.ini не найден: {ALEMBIC_CONFIG_PATH}")
			raise FileNotFoundError("Нет конфигурации Alembic")

		await apply_migrations()

		app.state.settings = settings
		log.info("[STARTUP] Инициализация завершена")

		yield
	except Exception as e:
		log.critical(f"[FATAL STARTUP ERROR] {e}", exc_info=True)
		raise RuntimeError("Критическая ошибка при старте приложения.") from e
	finally:
		await engine.dispose()
		log.info("[SHUTDOWN] Соединения с БД закрыты.")

app = FastAPI(
	title=settings.PROJECT_NAME,
	description=settings.DESCRIPTION,
	version=settings.VERSION,
	lifespan=lifespan,
)

# 1. CORS (внутренний — обрабатывает preflight)
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.BACKEND_CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)

# 2. Session (должен видеть правильный scheme от ProxyHeader для secure-куки)
app.add_middleware(
	SessionMiddleware,
	secret_key=settings.SECRET_KEY,
	session_cookie="webdnd_session",
	max_age=604800,  # 7 дней
	same_site="lax"
)

# 3. ProxyHeader (внешний — обновляет scheme до того, как Session проверит is_secure)
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

# --- СТАТИЧЕСКИЕ ФАЙЛЫ И ШАБЛОНЫ ---
static_dir = BASE_DIR / "frontend" / "static"
app.mount("/frontend/static", StaticFiles(directory=str(static_dir)), name="static")
templates_dir = BASE_DIR / "frontend" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
env = templates.env

def static_url(filename: str) -> str:
	file_dir = str("/frontend"+"/static/"+filename.lstrip('/'))
	return f"{file_dir}"

def b64encode_filter(value):
	return base64.b64encode(value).decode('utf-8')

env.filters['static_url'] = static_url
env.globals["static_url"] = static_url
env.filters['b64encode'] = b64encode_filter

# --- ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ОШИБОК ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
	return JSONResponse(status_code=422, content={"detail": f"Некорректные данные: {exc.errors()}"})

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
	if request.url.path.startswith("/api"):
		return JSONResponse(status_code=404, content={"detail": "Not found"})
	return HTMLResponse(content="<h1>404 - Страница не найдена</h1>", status_code=404)

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
os.environ['PROJECT_ROOT'] = str(BASE_DIR)
app.state.templates = templates
app.state.project_root = BASE_DIR

# --- ПОДКЛЮЧЕНИЕ РОУТЕРОВ ---
app.include_router(api_module.router)
app.include_router(web_module.router)
app.include_router(profile_module.router)

if __name__ == "__main__":
	uvicorn.run(
		"main:app",
		host="127.0.0.1",
		port=8080,
		log_level="info",
		reload=True
	)