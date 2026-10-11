# backend/app/schemas/auth.py

from Config.imports import (BaseModel, EmailStr, Field, field_validator, re, Optional)


class RegisterRequest(BaseModel):
	"""
	Схема входных данных для эндпоинта /auth/register.

	Исправление ошибки PydanticUserError:
	Параметр 'regex' заменен на 'pattern' для совместимости с v2.x.
	"""
	nickname: str = Field(
		...,
		min_length=3,
		max_length=32,
		pattern=r'^[\w\-]+$',  # <-- ИСПРАВЛЕНО: regex -> pattern
		description="Никнейм (латиница, цифры, дефис, подчеркивание)"
	)
	email: EmailStr = Field(..., description="Email пользователя")
	password: str = Field(
		...,
		min_length=8,
		max_length=128,
		description="Пароль"
	)
	accepted_terms: bool = Field(
		...,
		description="Согласие с пользовательским соглашением и политикой конфиденциальности"
	)

	@field_validator('password')
	@classmethod
	def check_password_complexity(cls, v: str) -> str:
		if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
			raise ValueError('Пароль должен содержать буквы и цифры')
		return v

	@field_validator('accepted_terms')
	@classmethod
	def check_terms_accepted(cls, v: bool) -> bool:
		if not v:
			raise ValueError('Нужно подтвердить согласие с пользовательским соглашением и политикой конфиденциальности')
		return v