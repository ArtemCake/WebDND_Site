# main.py

from Config.imports import (FastAPI, asynccontextmanager, CORSMiddleware, HTTPException, select,
                        StaticFiles, Jinja2Templates, base64, RequestValidationError, Request, asyncio,
						JSONResponse, HTMLResponse, Depends, uvicorn, APIRoute, os, pathlib)
from Config.Config import settings
from app.database.session import get_async_session_factory
import app.Routers.API_Routers as api_module
import app.Routers.Web_Routers as web_module
from app.enums.log_enums import LogAction, LogLevelEnum
from app.services.cleanup_on_start import cleanup_old_logs
from app.services.log_service import LogService
from app.services.user_service import UserService
from app.database._models import User
from alembic.command import upgrade
from alembic.config import Config
from app.database.database import engine, metadata


# --- ФУНКЦИЯ ПРИМЕНЕНИЯ МИГРАЦИЙ (СИНХРОННАЯ) ---
async def apply_migrations():
	try:

		print("[STARTUP] Применение миграций...")

		alembic_cfg = Config("alembic.ini")
		alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))
		upgrade(alembic_cfg, "head")
		await LogService.create_log(
			username=None,
			action=LogAction.DATABASE_MIGRATION,
			description="✅ Миграции БД успешно применены",
			log_level=LogLevelEnum.INFO
		)
		print("[STARTUP] ✅ Миграции БД успешно применены")
	except Exception as e:
		await LogService.create_log(
			username=None,
			action=LogAction.DATABASE_ERROR,
			description=f"⚠️ Ошибка при применении миграций: {str(e)}",
			log_level=LogLevelEnum.ERROR
		)
		raise

async def create_admin_user(session_factory):
	"""Вспомогательная функция для выноса логики админа."""
	async with session_factory as db:
		admin_password = settings.ADMIN_PASSWORD
		if admin_password:
			user_exists = await db.execute(select(User).where(User.username == "Admin"))
			if not user_exists.scalars().first():
				try:
					await UserService.register_new_user(
						db, username="Admin",
						password=admin_password.strip(),
						role="admin",
						gdpr_consent=True
					)
					await db.commit()
					await LogService.create_log(
						username="Admin",
						action=LogAction.REGISTER_SUCCESS,
						description="✅ Администратор успешно создан.",
						log_level=LogLevelEnum.INFO
					)
				except HTTPException as e:
					await LogService.create_log(
						username="Admin",
						action=LogAction.REGISTER_FAILED,
						description=f"⚠️ Не удалось создать админа: {e.detail}",
						log_level=LogLevelEnum.ERROR
					)
					raise

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""
	Lifespan теперь отвечает только за настройку состояния приложения.
	Миграции к этому моменту УЖЕ выполнены.
	"""
	try:
		print("[STARTUP] Проверка и создание таблиц...")
		# 2. Асинхронное создание всех таблиц из метаданных моделей.
		# Если таблицы существуют - команда отработает мгновенно.
		# Если нет - создаст всё дерево ForeignKey без ошибок циклов.
		async with engine.begin() as conn:
			await conn.run_sync(metadata.create_all)
		print("[STARTUP] Таблицы проверены/созданы успешно.")
		# Теперь создаем фабрику пулов для самого FastAPI
		session_factory = get_async_session_factory()
		app.state.session_factory = session_factory
		app.state.settings = settings
		# 3. Создаем админа через сервис (таблицы уже точно есть)
		await create_admin_user(session_factory)
		await cleanup_old_logs()
		yield
		# Корректное закрытие пулов соединений при остановке сервера
		await (await get_async_session_factory())().close()
	finally:
		# Важно корректно закрыть даже этот временный движок
		await engine.dispose()
		# Закрытие основного пула сессии
		await (await get_async_session_factory())().close()

def use_multipart_form_dep(dep):
	if hasattr(dep, "func"):
		for index, param in enumerate(dep.func.__annotations__.get("dependant", {}).get("params", [])):
			# Если параметр — это стандартная зависимость Form,
			# заменяем её на нашу OverloadedForm
			if param["type"] == "form" and param.get("default") is False:
				# Меняем тип зависимости
				param["__class__"] = "multipart_form"
	return dep

BASE_DIR = pathlib.Path(__file__).parent.resolve()

# --- СОЗДАНИЕ ПРИЛОЖЕНИЯ ---
app = FastAPI(
	title=settings.PROJECT_NAME,
	description=settings.DESCRIPTION,
	version=settings.VERSION,
	static_folder=str(BASE_DIR / "static"),
	static_url="/static",
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

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
os.environ['PROJECT_ROOT'] = str(BASE_DIR)
app.state.templates = templates
app.state.project_root = BASE_DIR
# Получаем окружение Jinja2 из глобального объекта templates
env = templates.env

@app.on_event("startup")
async def add_app_to_templates():
	# Добавляем экземпляр приложения в глобальные переменные всех шаблонов
	env.globals["app"] = app

def static_url(filename: str) -> str:
	return f"/static/{filename.lstrip('/')}"

env.globals["static_url"] = static_url

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


