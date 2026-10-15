# backend/app/Routers/api.py

from Config.logger import setup_logging
from backend.app.Services.rate_limit_service import check_ip_rate_limit
from backend.app.Services.security_service import (create_verification_token, verify_token, create_password_reset_token,
                                                   issue_login_session)
from backend.app.Services.user_service import (soft_delete_user, get_current_user, pwd_context)
from Config.Config import settings
from Config.imports import (JSONResponse, datetime, AsyncSession, update, UUID, RedirectResponse,
                            APIRouter, Depends, HTTPException, status, timedelta, hashlib,
                            Form, secrets, Request, CsrfProtect)
from backend.app.database.database import get_async_session
from backend.app.database.models.core.user import User
from backend.app.Services import security_service, user_service, mfa_service
from backend.app.Services.mail_service import mail_service
from backend.app.schemas.auth import RegisterRequest, validate_password_complexity

router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)

log = setup_logging(app_name="WorldLoom")

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user_action(
		request: Request,
		data: RegisterRequest,
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
	log.info(f"[AUTH][REGISTER] Attempt for {data.email}")
	try:
		existing_user = await user_service.get_user_by_email(session, data.email)
		if existing_user:
			log.warning(f"[AUTH][REGISTER] Duplicate attempt blocked for {data.email} (ID: {existing_user.id})")
			return JSONResponse(
				status_code=409,
				content={"error": "Пользователь с таким email уже существует"}
			)

		new_user = await user_service.create_user(
			session=session,
			nickname=data.nickname,
			email=data.email,
			password=data.password
		)

		new_user.profile_settings = {
			**(new_user.profile_settings or {}),
			"terms_accepted_at": datetime.utcnow().isoformat(),
			"terms_version": "1.0"
		}
		session.add(new_user)
		await session.commit()
		await session.refresh(new_user)

		verification_token = create_verification_token(new_user.id)
		success = await mail_service.send_verification_email(
			user_name=new_user.nickname,
			user_email=new_user.email,
			verification_token=verification_token
		)

		if not success:
			log.error(f"[AUTH][MAIL_FAIL] Failed to send verification for {new_user.id}")
			return JSONResponse(
				status_code=201,
				content={
					"message": "Регистрация успешна, но ошибка отправки письма.",
					"resend_url": f"{settings.API_V1_STR}/auth/resend-verification/{new_user.id}"
				}
			)

		log.info(f"[AUTH][REGISTER] Success for {data.email} (ID: {new_user.id})")
		return JSONResponse(
			status_code=201,
			content={
			"message": "Регистрация успешна! Письмо отправлено.",
			"resend_url": f"{settings.API_V1_STR}/auth/resend-verification/{new_user.id}"
			}
		)

	except Exception as e:
		log.error(f"Critical server error during user registration for email '{data.email}'", exc_info=True)
		return JSONResponse(
			status_code=500,
			content={"error": "Непредвиденная ошибка сервера. Администраторы уведомлены."}
		)

@router.post("/login", response_model=dict)
async def login_for_access_token(
		request: Request,
		email: str = Form(...),
		password: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)

	client_ip = request.client.host if request.client else "unknown"
	if await check_ip_rate_limit(client_ip, settings.LOGIN_IP_RATE_LIMIT, settings.LOGIN_IP_RATE_WINDOW_MINUTES):
		log.warning(f"[AUTH][RATE_LIMIT] Too many login attempts from {client_ip}")
		return JSONResponse(status_code=429, content={"error": "Слишком много попыток входа. Попробуйте позже."})

	log.info(f"[AUTH][LOGIN] Attempt for {email} from {client_ip}")
	access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

	try:
		user_record = await user_service.get_user_by_email(session, email)
		if not user_record:
			log.warning(f"[AUTH][FAILED] Account does not exist for {email}")
			return JSONResponse(status_code=401, content={"error": "Аккаунт не найден.", "action": "account_not_found"})
		if user_record.locked_until:
			locked_naive = user_record.locked_until.replace(tzinfo=None)
			if locked_naive > datetime.utcnow():
				retry_after = int((user_record.locked_until - datetime.utcnow()).total_seconds())
				log.warning(f"[AUTH][LOCKED] Login blocked for {email}, retry in {retry_after}s")
				return JSONResponse(status_code=429, content={
					"error": "Аккаунт временно заблокирован из-за множества неверных попыток входа.",
					"retry_after_seconds": retry_after
				})

		user = await user_service.authenticate_user(session, email, password)
		if not user or not user.is_active:
			log.warning(f"[AUTH][FAILED] Invalid credentials or inactive account for {email}")
			await user_service.register_failed_login(session, user_record)
			return JSONResponse(status_code=401, content={"error": "Неверный пароль."})

		await user_service.reset_login_lockout(session, user)

		await user_service.reset_login_lockout(session, user)

		if user.is_2fa_enabled:
			mfa_token = security_service.create_mfa_pending_token(str(user.id))
			log.info(f"[AUTH][MFA] Password OK, awaiting TOTP for {email} (ID: {user.id})")
			return JSONResponse(status_code=200, content={
				"mfa_required": True,
				"mfa_token": mfa_token,
				"message": "Введите код двухфакторной аутентификации."
			})

		return await issue_login_session(user, session)

	except PermissionError as e:
		log.warning(f"[AUTH][BLOCKED] Account state issue during login for {email}: {e}")
		return JSONResponse(status_code=403, content={"error": "Доступ запрещен."})
	except Exception as e:
		log.error(f"Critical error during login for '{email}'", exc_info=True)
		return JSONResponse(status_code=500, content={"error": "Непредвиденная ошибка сервера."})

@router.post("/login/verify-mfa", response_model=dict)
async def login_verify_mfa(
		request: Request,
		mfa_token: str = Form(...),
		code: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)

	client_ip = request.client.host if request.client else "unknown"
	rate_limit_key = f"{client_ip}:mfa_verify"
	if await check_ip_rate_limit(rate_limit_key, settings.LOGIN_IP_RATE_LIMIT, settings.LOGIN_IP_RATE_WINDOW_MINUTES):
		log.warning(f"[AUTH][MFA][RATE_LIMIT] Too many code attempts from {client_ip}")
		return JSONResponse(status_code=429, content={"error": "Слишком много попыток. Попробуйте позже."})

	payload = security_service.verify_token(mfa_token, purpose="mfa_pending")
	user_id = payload.get("sub") if payload else None
	if not user_id:
		return JSONResponse(status_code=400, content={"error": "Сессия входа истекла, войдите заново."})

	user = await user_service.get_user_by_id(session, user_id)
	if not user or not user.is_active or not user.is_2fa_enabled:
		return JSONResponse(status_code=400, content={"error": "Сессия входа недействительна."})

	if not await mfa_service.verify_login_code(session, user, code):
		log.warning(f"[AUTH][MFA][FAILED] Invalid code for {user.email}")
		return JSONResponse(status_code=401, content={"error": "Неверный код."})

	return await issue_login_session(user, session)

@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_async_session)):
	"""Подтверждение адреса почты."""
	payload = verify_token(token, purpose="email_verification")
	user_id: str = payload.get("sub") if payload else None

	if not user_id:
		log.warning("[AUTH][VERIFY] Invalid or expired token provided.")
		# Было: raise HTTPException(status_code=400, ...) — пользователь видел голый JSON.
		# Теперь отправляем на страницу входа с пометкой об ошибке в query-параметре.
		return RedirectResponse(url="/login?verify=invalid", status_code=status.HTTP_303_SEE_OTHER)

	success = await user_service.verify_email(session, user_id)
	if not success:
		log.error(f"[AUTH][VERIFY] User ID {user_id} not found in DB.")
		return RedirectResponse(url="/login?verify=notfound", status_code=status.HTTP_303_SEE_OTHER)

	log.info(f"[AUTH][VERIFY] Email verified for user ID {user_id}.")
	# Было: JSONResponse({"message": "Email успешно подтвержден."}) — теперь переход на вход.
	return RedirectResponse(url="/login?verify=success", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/resend-verification/{user_id}", response_model=dict)
async def resend_verification_email(
		user_id: UUID,
		request: Request,
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	"""Повторная отправка письма подтверждения почты."""
	await csrf_protect.validate_csrf(request)
	target_user = await user_service.get_user_by_id(session, user_id)

	if not target_user:
		raise HTTPException(status_code=404, detail="Пользователь не найден.")

	if target_user.is_email_verified:
		return JSONResponse(
			status_code=200,
			content={"message": "Почта уже подтверждена, письмо не отправлено."}
		)

	verification_token = create_verification_token(target_user.id)

	try:
		await mail_service.send_verification_email(
			user_name=target_user.nickname,
			user_email=target_user.email,
			verification_token=verification_token
		)
	except Exception as e:
		log.error(f"[AUTH][RESEND] Failed to send verification email to {target_user.email}: {e}")
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Не удалось отправить письмо. Попробуйте позже."
		)

	log.info(f"[AUTH][RESEND] Verification email re-sent for {target_user.id}")
	return JSONResponse(
		status_code=200,
		content={"message": "Письмо с подтверждением отправлено повторно."}
	)

@router.post("/logout")
async def logout(
		request: Request,
		current_user: User = Depends(get_current_user),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)
	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=None, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	response = JSONResponse(content={"message": "Выход выполнен успешно"})
	response.delete_cookie(key="access_token", path="/")
	response.delete_cookie(key="refresh_token", path="/")
	response.headers["HX-Redirect"] = "/login"

	log.info(f"[AUTH][LOGOUT] Session invalidated and cookies cleared for {current_user.id}.")
	return response

@router.post("/delete-account")
async def delete_account(
		request: Request,
		password: str = Form(...),
		permanent: bool = Form(False),
		db: AsyncSession = Depends(get_async_session),
		current_user: User = Depends(get_current_user),
		csrf_protect: CsrfProtect = Depends()
):
	"""Удаление аккаунта."""
	await csrf_protect.validate_csrf(request)

	if not current_user.password_hash:
		log.warning(f"[ACCOUNT][DELETE] No local password set (OAuth-only account) for {current_user.id}")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Для этого аккаунта не задан пароль (вход через соцсеть). Удаление по паролю недоступно.",
		)

	if not pwd_context.verify(password, current_user.password_hash):
		log.warning(f"[ACCOUNT][DELETE] Wrong password attempt for {current_user.id}")
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Неверный пароль.",
			headers={"WWW-Authenticate": "Bearer"},
		)

	if permanent:
		await user_service.hard_delete_user(db, current_user.id)
		action_log = "Account permanently deleted."
	else:
		success = await soft_delete_user(db, current_user.id)
		if not success:
			log.error(f"[ACCOUNT][DELETE] Soft delete failed for {current_user.id}")
			raise HTTPException(status_code=404, detail="Пользователь не найден или уже удален.")
		action_log = "Account marked as deleted."

	stmt = (
		update(User)
		.where(User.id == current_user.id)
		.values(active_session_token=None, updated_at=datetime.utcnow())
	)
	await db.execute(stmt)
	await db.commit()

	log.info(f"[ACCOUNT][DELETED] Account {current_user.id} processed. Action: {action_log}")

	response = JSONResponse(content={"message": "Аккаунт удалён."})
	response.delete_cookie(key="access_token", path="/")
	response.delete_cookie(key="refresh_token", path="/")
	response.headers["HX-Redirect"] = "/login"
	return response

@router.post("/refresh", response_model=dict)
async def refresh_access_token(
		request: Request,
		session: AsyncSession = Depends(get_async_session),
):
	"""Выдача новой пары токенов по refresh_token из cookie."""
	refresh_token = request.cookies.get("refresh_token")
	if not refresh_token:
		raise HTTPException(status_code=401, detail="Refresh-токен отсутствует.")

	try:
		payload = security_service.jwt.decode(
			refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
		)
	except security_service.JWTError:
		raise HTTPException(status_code=401, detail="Недействительный refresh-токен.")

	if payload.get("type") != "refresh":
		log.warning("[AUTH][REFRESH] Token with wrong type used as refresh.")
		raise HTTPException(status_code=401, detail="Недействительный refresh-токен.")

	user_id = payload.get("sub")
	token_sid = payload.get("sid")
	user = await user_service.get_user_by_id(session, user_id)

	if not user or not user.is_active or user.active_session_token != token_sid:
		log.warning(f"[AUTH][REFRESH] Session revoked or user inactive for {user_id}.")
		raise HTTPException(status_code=401, detail="Сессия завершена, войдите снова.")

	new_session_token = secrets.token_urlsafe(64)
	tokens = await security_service.create_jwt_pair(
		user_obj_or_id=user,
		session_token=new_session_token
	)

	stmt = (
		update(User)
		.where(User.id == user.id)
		.values(active_session_token=new_session_token, updated_at=datetime.utcnow())
	)
	await session.execute(stmt)
	await session.commit()

	response = JSONResponse(content={"message": "Токен обновлён."})
	response.set_cookie(
		key="access_token", value=tokens["access_token"],
		httponly=True, samesite="lax", path="/",
		max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, secure=settings.SECURE_COOKIES
	)
	response.set_cookie(
		key="refresh_token", value=tokens["refresh_token"],
		httponly=True, samesite="lax", path="/",
		max_age=7 * 24 * 60 * 60, secure=settings.SECURE_COOKIES
	)
	log.info(f"[AUTH][REFRESH] Tokens refreshed for {user.id}")
	return response

@router.post("/forgot-password", response_model=dict)
async def forgot_password(
		request: Request,
		email: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	"""
	Запрос на восстановление пароля. Ответ намеренно одинаковый независимо
	от того, существует ли такой email, — иначе по ответу можно было бы
	проверять, какие адреса зарегистрированы (перечисление аккаунтов).
	"""
	await csrf_protect.validate_csrf(request)

	client_ip = request.client.host if request.client else "unknown"
	# Отдельный ключ бакета (":password_reset"), чтобы не делить счётчик
	# попыток с /auth/login — иначе спам сюда блокировал бы и вход по IP.
	rate_limit_key = f"{client_ip}:password_reset"
	if await check_ip_rate_limit(rate_limit_key, settings.LOGIN_IP_RATE_LIMIT, settings.LOGIN_IP_RATE_WINDOW_MINUTES):
		log.warning(f"[AUTH][RATE_LIMIT] Too many password reset requests from {client_ip}")
		return JSONResponse(status_code=429, content={"error": "Слишком много попыток. Попробуйте позже."})

	generic_response = JSONResponse(status_code=200, content={
		"message": "Если такой email зарегистрирован, на него отправлена ссылка для восстановления пароля."
	})

	user = await user_service.get_user_by_email(session, email)
	if not user or not user.is_active or not user.password_hash:
		# Нет аккаунта, деактивирован или это OAuth-only без локального пароля —
		# наружу в любом случае уходит один и тот же нейтральный ответ.
		log.info(f"[AUTH][FORGOT_PASSWORD] No-op for {email}")
		return generic_response

	reset_token = create_password_reset_token(user)

	try:
		await mail_service.send_password_reset(user_email=user.email, reset_token=reset_token, valid_minutes=30)
	except Exception as e:
		log.error(f"[AUTH][FORGOT_PASSWORD] Failed to send reset email to {user.email}: {e}")

	log.info(f"[AUTH][FORGOT_PASSWORD] Reset link issued for {user.id}")
	return generic_response


@router.post("/reset-password", response_model=dict)
async def reset_password_action(
		request: Request,
		token: str = Form(...),
		new_password: str = Form(...),
		session: AsyncSession = Depends(get_async_session),
		csrf_protect: CsrfProtect = Depends()
):
	await csrf_protect.validate_csrf(request)

	payload = verify_token(token, purpose="password_reset")
	user_id = payload.get("sub") if payload else None
	if not user_id:
		return JSONResponse(status_code=400, content={"error": "Ссылка недействительна или устарела."})

	user = await user_service.get_user_by_id(session, user_id)
	if not user or not user.is_active or not user.password_hash:
		return JSONResponse(status_code=400, content={"error": "Ссылка недействительна."})

	current_fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]
	if payload.get("pwfp") != current_fingerprint:
		log.warning(f"[AUTH][RESET_PASSWORD] Reused or stale token for {user.id}")
		return JSONResponse(status_code=400, content={"error": "Ссылка уже использована или устарела."})

	if not (8 <= len(new_password) <= 128):
		return JSONResponse(status_code=400, content={"error": "Пароль должен быть от 8 до 128 символов."})

	complexity_error = validate_password_complexity(new_password)
	if complexity_error:
		return JSONResponse(status_code=400, content={"error": complexity_error})

	await user_service.reset_password(session, user, new_password)
	log.info(f"[AUTH][RESET_PASSWORD] Password reset completed for {user.id}")

	return JSONResponse(status_code=200, content={
		"message": "Пароль успешно изменён. Теперь можно войти с новым паролем.",
		"redirect_url": "/login"
	})