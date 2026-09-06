# backend/app/Services/mail_service.py

"""
Сервис отправки email-уведомлений.
Реализует требования ТЗ: подтверждение регистрации, восстановление пароля, системные оповещения.
Использует асинхронный SMTP (aiosmtplib) для неблокирующей работы FastAPI.
"""

from Config.Config import settings
from Config.imports import (asyncio, MIMEText, MIMEMultipart, Environment, FileSystemLoader,
                            select_autoescape, Path, List, Optional, ssl, SMTP)


class MailService:
	def __init__(self):
		# Настройки Jinja2 для рендеринга HTML-шаблонов писем
		templates_dir = Path(__file__).resolve().parent.parent / "templates" / "emails"
		self.env = Environment(
			loader=FileSystemLoader(str(templates_dir)),
			autoescape=select_autoescape(["html", "xml"])
		)

		# Настройки SMTP
		self.smtp_host = settings.SMTP_HOST
		self.smtp_port = settings.SMTP_PORT
		self.smtp_user = settings.SMTP_USER
		self.smtp_password = settings.SMTP_PASSWORD
		self.use_tls = settings.SMTP_USE_TLS
		self.use_ssl = settings.SMTP_USE_SSL

		self.sender_name = settings.MAIL_SENDER_NAME
		self.sender_email = settings.MAIL_SENDER_EMAIL

	async def _get_smtp_connection(self) -> SMTP:
		"""Устанавливает и возвращает асинхронное соединение с SMTP-сервером."""
		security = None
		if self.use_ssl:
			security = "implicit"
		elif self.use_tls:
			security = "starttls"

		return SMTP(
			hostname=self.smtp_host,
			port=self.smtp_port,
			username=self.smtp_user,
			password=self.smtp_password,
			use_tls=self.use_tls,
			validate_certs=True,
			tls_context=ssl.create_default_context() if self.use_tls else None,
			start_tls=bool(self.use_tls),
			tls_type=security
		)

	def _render_template(self, template_name: str, context: dict) -> str:
		"""Рендерит HTML-шаблон письма."""
		template = self.env.get_template(template_name)
		return template.render(**context)

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
		Низкоуровневая отправка письма.
		Возвращает True при успехе, False при ошибке.
		"""
		msg = MIMEMultipart("alternative")
		msg["Subject"] = subject
		msg["From"] = f"{self.sender_name} <{self.sender_email}>"
		msg["To"] = to_email

		if cc:
			msg["Cc"] = ", ".join(cc)
		if bcc:
			msg["Bcc"] = ", ".join(bcc)

		part1 = MIMEText(text_content or "Это HTML-письмо. Пожалуйста, просмотрите его в почтовом клиенте, поддерживающем HTML.", "plain", "utf-8")
		part2 = MIMEText(html_content, "html", "utf-8")

		msg.attach(part1)
		msg.attach(part2)

		smtp = None
		try:
			smtp = await self._get_smtp_connection()
			await smtp.connect()
			if self.use_tls and not self.use_ssl:
				await smtp.starttls()
			if self.smtp_user and self.smtp_password:
				await smtp.login(self.smtp_user, self.smtp_password)

			recipients = [to_email]
			if cc:
				recipients.extend(cc)
			if bcc:
				recipients.extend(bcc)

			await smtp.send_message(msg, sender=self.sender_email, recipients=recipients)
			return True
		except Exception as e:
			# В production здесь должен быть вызов Sentry или логирование в SystemEvent
			print(f"[MAIL ERROR] Failed to send email to {to_email}. Error: {str(e)}")
			return False
		finally:
			if smtp:
				try:
					await smtp.quit()
				except Exception:
					pass

	# --- ВЫСОКОУРОВНЕВЫЕ МЕТОДЫ ДЛЯ БИЗНЕС-ЛОГИКИ ---

	async def send_verification_email(self, user_email: str, verification_token: str) -> bool:
		"""Отправка письма для подтверждения регистрации."""
		context = {
			"user_email": user_email,
			"frontend_url": settings.FRONTEND_URL,
			"verification_token": verification_token,
			"support_email": settings.MAIL_SUPPORT_EMAIL
		}

		html = self._render_template("verification_email.html", context)
		text = f"Для подтверждения регистрации перейдите по ссылке: {settings.FRONTEND_URL}/verify-email?token={verification_token}"

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