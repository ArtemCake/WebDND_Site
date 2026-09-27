# Config/csrf_config.py

from Config.imports import (BaseModel, CsrfProtect)
from Config.Config import settings


class CsrfSettings(BaseModel):
	secret_key: str = settings.SECRET_KEY
	cookie_samesite: str = "lax"
	cookie_secure: bool = settings.SECURE_COOKIES
	header_name: str = "X-CSRF-Token"


@CsrfProtect.load_config
def get_csrf_config():
	return CsrfSettings()