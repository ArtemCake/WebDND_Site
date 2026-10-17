# backend/app/Core/csrf.py

from Config.imports import (Request, Depends, CsrfProtect)


async def enforce_csrf(
		request: Request,
		csrf_protect: CsrfProtect = Depends(),
) -> None:
	"""Единая точка CSRF-проверки для всех мутирующих роутов.
	Любой POST/PATCH/PUT/DELETE должен подключать её явно —
	либо на уровне роутера, либо в сигнатуре конкретного эндпоинта."""
	await csrf_protect.validate_csrf(request)
