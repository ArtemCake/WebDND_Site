# backend/app/Routers/web.py

from Config.Config import settings
from Config.imports import HTMLResponse, os, URLSafeTimedSerializer, APIRouter


# Создаем "подписыватель" (signer) для данных.
secret_key = os.environ.get("SECRET_KEY", settings.SECRET_KEY)
serializer = URLSafeTimedSerializer(secret_key)

web_router = APIRouter()

@web_router.get("/", response_class=HTMLResponse)
async def get_main_page():
	return """
    <html>
        <head><title>WebDND Site</title></head>
        <body>
            <h1>Добро пожаловать в WebDND API</h1>
            <p>Документация доступна по адресу /docs</p>
        </body>
    </html>
    """


