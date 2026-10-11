# backend/app/Services/mail_service.py

"""
Сервис отправки email-уведомлений.
Реализует требования ТЗ: подтверждение регистрации, восстановление пароля, системные оповещения.
Использует асинхронный SMTP (aiosmtplib) для неблокирующей работы FastAPI.
"""

from Config.Config import settings
from Config.logger import setup_logging
from Config.imports import (MIMEText, MIMEMultipart, Environment, FileSystemLoader,
                            select_autoescape, List, Optional, ssl, SMTP)


log = setup_logging(app_name="WebDND_Site")

class MailService:
	def __init__(self):
		# Настройки Jinja2 для рендеринга HTML-шаблонов писем
		templates_dir = settings._base_dir / "frontend" / "templates" / "emails"
		self.env = Environment(
			loader=FileSystemLoader(str(templates_dir)),
			autoescape=select_autoescape(["html", "xml"])
		)

		# Настройки SMTP (основной провайдер)
		self.smtp_host = settings.SMTP_HOST
		self.smtp_port = settings.SMTP_PORT
		self.smtp_user = settings.SMTP_USER
		self.smtp_password = settings.SMTP_PASSWORD
		self.use_tls = settings.SMTP_USE_TLS
		self.use_ssl = settings.SMTP_USE_SSL

		# Резервный SMTP-провайдер. Поля опциональны: если SMTP_FALLBACK_HOST
		# не задан в .env, резерв просто не используется и поведение как раньше.
		self.fallback_host = getattr(settings, "SMTP_FALLBACK_HOST", None)
		self.fallback_port = getattr(settings, "SMTP_FALLBACK_PORT", None)
		self.fallback_user = getattr(settings, "SMTP_FALLBACK_USER", None)
		self.fallback_password = getattr(settings, "SMTP_FALLBACK_PASSWORD", None)
		self.fallback_use_tls = getattr(settings, "SMTP_FALLBACK_USE_TLS", True)
		self.fallback_use_ssl = getattr(settings, "SMTP_FALLBACK_USE_SSL", False)

		self.sender_name = settings.MAIL_SENDER_NAME
		self.sender_email = settings.MAIL_SENDER_EMAIL
		self.fallback_sender_email = getattr(settings, "MAIL_FALLBACK_SENDER_EMAIL", self.fallback_user)

	async def _get_smtp_connection(self, use_fallback: bool = False) -> SMTP:
		"""
		Создаёт объект SMTP-соединения.
		Для SSL (порт 465) — implicit TLS.
		Для STARTTLS (порт 587) — обычное соединение, upgrade до TLS вызывается отдельно в _try_send.
		use_fallback=True — подключение к резервному провайдеру вместо основного.
		"""
		host = self.fallback_host if use_fallback else self.smtp_host
		port = self.fallback_port if use_fallback else self.smtp_port
		use_ssl = self.fallback_use_ssl if use_fallback else self.use_ssl
		use_tls = self.fallback_use_tls if use_fallback else self.use_tls

		if use_ssl:
			return SMTP(
				hostname=host,
				port=port,
				use_tls=True,
				validate_certs=True,
				tls_context=ssl.create_default_context(),
			)
		else:
			return SMTP(
				hostname=host,
				port=port,
				use_tls=False,
				validate_certs=True,
				tls_context=ssl.create_default_context() if use_tls else None,
			)

	def _render_template(self, template_name: str, context: dict) -> str:
		"""Рендерит HTML-шаблон письма."""
		template = self.env.get_template(template_name)
		return template.render(**context)

	async def _try_send(self, msg: MIMEMultipart, recipients: List[str], use_fallback: bool) -> bool:
		"""Один фактический проход отправки — через основной либо резервный SMTP."""
		smtp = None
		user = self.fallback_user if use_fallback else self.smtp_user
		password = self.fallback_password if use_fallback else self.smtp_password
		use_tls = self.fallback_use_tls if use_fallback else self.use_tls
		use_ssl = self.fallback_use_ssl if use_fallback else self.use_ssl
		sender = self.fallback_sender_email if use_fallback else self.sender_email

		# Подменяем From на адрес, соответствующий реально используемому провайдеру
		del msg["From"]
		msg["From"] = f"{self.sender_name} <{sender}>"

		try:
			smtp = await self._get_smtp_connection(use_fallback=use_fallback)
			await smtp.connect()

			if use_tls and not use_ssl:
				await smtp.starttls()

			if user and password:
				await smtp.login(user, password)

			await smtp.send_message(msg, sender=sender, recipients=recipients)
			return True
		finally:
			if smtp:
				try:
					await smtp.quit()
				except Exception:
					pass

	async def send_email(
			self,
			to_email: str,
			subject: str,
			html_content: str,
			text_content: Optional[str] = None,
			cc: Optional[List[str]] = None,
			bcc: Optional[List[str]] = None
	) -> bool:
		"""
		Отправка письма. Возвращает True при успехе, False при ошибке.
		Сначала пробует основной SMTP-провайдер; если он падает и настроен
		резервный (SMTP_FALLBACK_HOST в .env), автоматически пробует его.
		"""
		msg = MIMEMultipart("alternative")
		msg["Subject"] = subject
		msg["From"] = f"{self.sender_name} <{self.sender_email}>"
		msg["To"] = to_email

		if cc:
			msg["Cc"] = ", ".join(cc)

		part1 = MIMEText(text_content or "Это HTML-письмо. Пожалуйста, просмотрите его в почтовом клиенте, поддерживающем HTML.", "plain", "utf-8")
		part2 = MIMEText(html_content, "html", "utf-8")

		msg.attach(part1)
		msg.attach(part2)

		recipients = [to_email]
		if cc:
			recipients.extend(cc)
		if bcc:
			recipients.extend(bcc)

		try:
			return await self._try_send(msg, recipients, use_fallback=False)
		except Exception as e:
			log.error(f"[MAIL][PRIMARY_FAIL] host={self.smtp_host} to={to_email} subject='{subject}': {e}")

		if self.fallback_host:
			try:
				log.warning(f"[MAIL][FALLBACK_TRY] host={self.fallback_host} to={to_email}")
				result = await self._try_send(msg, recipients, use_fallback=True)
				if result:
					log.info(f"[MAIL][FALLBACK_OK] to={to_email} subject='{subject}'")
				return result
			except Exception as e:
				log.error(f"[MAIL][FALLBACK_FAIL] host={self.fallback_host} to={to_email} subject='{subject}': {e}")
				return False

		log.error(f"[MAIL][NO_FALLBACK] Резервный провайдер не настроен, письмо к {to_email} не отправлено.")
		return False

	# --- ВЫСОКОУРОВНЕВЫЕ МЕТОДЫ ДЛЯ БИЗНЕС-ЛОГИКИ ---

	async def send_verification_email(self, user_name: str, user_email: str, verification_token: str) -> bool:
		"""Отправка письма для подтверждения регистрации."""
		verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"

		context = {
			"user_name": user_name,
			"user_email":user_email,
			"frontend_url": settings.FRONTEND_URL,
			"verification_token": verification_token,
			"verification_url": verification_url,
			"support_email": settings.MAIL_SUPPORT_EMAIL
		}

		html = self._render_template("verification_email.html", context)
		text = f"Для подтверждения регистрации перейдите по ссылке: {verification_url}"

		subject = "Подтвердите регистрацию в WebDND"
		return await self.send_email(to_email=user_email, subject=subject, html_content=html, text_content=text)

	async def send_password_reset(self, user_email: str, reset_token: str) -> bool:
		"""Отправка ссылки для сброса пароля."""
		context = {
			"user_email": user_email,
			"frontend_url": settings.FRONTEND_URL,
			"reset_token": reset_token,
			"valid_minutes": int(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
		}

		html = self._render_template("password_reset.html", context)
		text = f"Для сброса пароля перейдите по ссылке: {settings.FRONTEND_URL}/reset-password?token={reset_token}"

		subject = "Сброс пароля WebDND"
		return await self.send_email(to_email=user_email, subject=subject, html_content=html, text_content=text)

	async def send_invite_to_game(self, to_email: str, master_nickname: str, game_title: str, invite_token: str) -> bool:
		"""Приглашение игрока в игру по email."""
		context = {
			"master_nickname": master_nickname,
			"game_title": game_title,
			"frontend_url": settings.FRONTEND_URL,
			"invite_token": invite_token
		}

		html = self._render_template("game_invite.html", context)
		text = f"{master_nickname} пригласил вас в игру '{game_title}'. Ссылка: {settings.FRONTEND_URL}/accept-invite?token={invite_token}"

		subject = f"Приглашение в игру: {game_title}"
		return await self.send_email(to_email=to_email, subject=subject, html_content=html, text_content=text)

	async def send_system_alert(self, subject: str, html_body: str, admin_emails: List[str]) -> bool:
		"""Отправка критического алерта администраторам."""
		success = True
		for email in admin_emails:
			if not await self.send_email(to_email=email, subject=subject, html_content=html_body):
				success = False
		return success

# Глобальный экземпляр сервиса (рекомендуется использовать в FastAPI через Depends)
mail_service = MailService()