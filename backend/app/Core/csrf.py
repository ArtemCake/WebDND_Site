# backend/app/Core/csrf.py

from dataclasses import dataclass, field
from itsdangerous import BadData, URLSafeTimedSerializer
from starlette.responses import Response
from Config.imports import Request, Depends, CsrfProtect


_CSRF_SALT = "fastapi-csrf-token"
_REQUEST_STATE_KEY = "_worldloom_csrf_page_tokens"


@dataclass(frozen=True)
class CsrfPageTokens:
	"""CSRF-данные для HTML-страницы.

	signed_token заполнен только при создании новой пары.
	При переиспользовании cookie повторно устанавливать её не нужно.
	"""

	token: str = field(repr=False)
	signed_token: str | None = field(default=None, repr=False)


def ensure_csrf_tokens(request: Request, csrf_protect: CsrfProtect) -> CsrfPageTokens:
	"""Получить действующий токен страницы или создать новую пару.

	Используется при выдаче HTML, а не для разрешения POST-запросов.

	Адаптер рассчитан на fastapi-csrf-protect 1.0.7:
	использует те же настройки, соль и сериализатор,
	что generate_csrf_tokens() и validate_csrf() библиотеки.
	"""

	# Повторный вызов в рамках одного запроса должен вернуть
	# ту же пару, даже если входящий запрос ещё не содержит cookie.
	cached = getattr(request.state, _REQUEST_STATE_KEY, None)

	if isinstance(cached, CsrfPageTokens):
		return cached

	# У библиотеки 1.0.7 нет публичного метода извлечения
	# исходного токена из подписанной cookie.
	# Доступ к её внутренним настройкам сосредоточен здесь.
	secret_key = csrf_protect._secret_key

	if secret_key is None:
		raise RuntimeError(
			"Для работы CSRF необходимо настроить secret_key."
		)

	signed_cookie = request.cookies.get(csrf_protect._cookie_key)

	if signed_cookie:
		serializer = URLSafeTimedSerializer(
			secret_key,
			salt=_CSRF_SALT,
		)

		try:
			token = serializer.loads(
				signed_cookie,
				max_age=csrf_protect._max_age,
			)
		except BadData:
			# Включает некорректную подпись, повреждённые данные
			# и истёкший срок действия подписи.
			pass
		else:
			if isinstance(token, str) and token:
				tokens = CsrfPageTokens(token=token)

				setattr(request.state, _REQUEST_STATE_KEY, tokens)

				return tokens

	# Cookie отсутствует, повреждена, просрочена
	# или содержит неподходящие данные.
	token, signed_token = csrf_protect.generate_csrf_tokens()

	tokens = CsrfPageTokens(
		token=token,
		signed_token=signed_token,
	)

	setattr(request.state, _REQUEST_STATE_KEY, tokens)

	return tokens

def apply_csrf_tokens(response: Response, csrf_protect: CsrfProtect, tokens: CsrfPageTokens) -> None:
	"""Добавить CSRF-данные именно в возвращаемый браузеру ответ."""

	if tokens.signed_token is not None:
		csrf_protect.set_csrf_cookie(tokens.signed_token, response)

	response.headers["X-CSRF-Token"] = tokens.token

	# HTML с CSRF-токеном не должен сохраняться в общем кеше.
	response.headers["Cache-Control"] = "no-store"

async def enforce_csrf(request: Request, csrf_protect: CsrfProtect = Depends()) -> None:
	"""Единая точка CSRF-проверки для всех мутирующих роутов.

	Любой POST/PATCH/PUT/DELETE должен подключать её явно:
	на уровне роутера или конкретного эндпоинта.
	"""

	await csrf_protect.validate_csrf(request)