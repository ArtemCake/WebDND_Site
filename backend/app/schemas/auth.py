# backend/app/schemas/auth.py

from Config.imports import (BaseModel, EmailStr, Field, field_validator, Optional, re)


class LoginRequest(BaseModel):
	"""Схема входных данных для эндпоинта /auth/login"""
	email: EmailStr = Field(..., description="Email пользователя")
	password: str = Field(..., min_length=8, max_length=128, description="Пароль")

	@field_validator('password')
	@classmethod
	def check_password_complexity(cls, v: str) -> str:
		# Проверка сложности: минимум одна буква и одна цифра
		if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
			raise ValueError('Пароль должен содержать буквы и цифры')
		return v

class RegisterRequest(BaseModel):
	"""Схема входных данных для эндпоинта /auth/register"""
	nickname: str = Field(..., min_length=3, max_length=32,
	                      regex=r'^[\w\-]+$',
	                      description="Никнейм (латиница, цифры, дефис, подчеркивание)")
	email: EmailStr = Field(..., description="Email пользователя")
	password: str = Field(..., min_length=8, max_length=128, description="Пароль")

	@field_validator('password')
	@classmethod
	def check_password_complexity(cls, v: str) -> str:
		if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
			raise ValueError('Пароль должен содержать буквы и цифры')
		return v

class UpdateProfileRequest(BaseModel):
	"""Схема обновления профиля"""
	nickname: Optional[str] = Field(None, min_length=3, max_length=32, regex=r'^[\w\-]+$')
	email: Optional[EmailStr] = None

class ChangePasswordRequest(BaseModel):
	current_password: str = Field(..., min_length=8)
	new_password: str = Field(..., min_length=8, max_length=128)

	@field_validator('new_password')
	@classmethod
	def check_new_password_complexity(cls, v: str) -> str:
		if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
			raise ValueError('Новый пароль должен содержать буквы и цифры')
		return v