# Config/imports.py

"""
Централизованный импорт зависимостей для предотвращения циклических импортов 
и обеспечения строгой типизации во всем проекте WebDND_Site.
"""

# --- Стандартная библиотека ---
import os
import re
import ssl
import sys
import time
import base64
import argon2
import pathlib
import asyncio
import logging
import secrets
import uvicorn
import atexit
from queue import Queue
from sqlalchemy.future import select
from enum import Enum, StrEnum
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Type, Union
from uuid import UUID, uuid4
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener

# --- База данных (SQLAlchemy) ---
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker, create_async_engine)
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base, backref
from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Index, Float,	Integer, Table, Column,
	String,	Text, UniqueConstraint,	text, func, CheckConstraint, SmallInteger, update)
from sqlalchemy.dialects.postgresql import INET, JSONB, ARRAY, UUID as PG_UUID, ENUM as PG_ENUM
from sqlalchemy.types import TIMESTAMP
from geoalchemy2 import Geometry, Geography

# --- Веб-сервер (FastAPI & Starlette) ---
from fastapi import (APIRouter,	Depends, FastAPI, File, Form, HTTPException,
	Request, Response, status, UploadFile)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.exceptions import TemplateNotFound
from aiosmtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- Конфигурация окружения ---
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Безопасность и аутентификация ---
from argon2 import PasswordHasher
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import ( CsrfProtectError, MissingTokenError, TokenValidationError, InvalidHeaderError )

# --- Утилиты файлов и путей ---
from itsdangerous import URLSafeTimedSerializer

# --- Утилиты путей и конфигурации ---
from pathlib import Path

# --- Валидация API (Pydantic) ---
from pydantic import ValidationError, EmailStr, BaseModel, Field
from fastapi.exceptions import RequestValidationError

# --- Роутинг ---
from fastapi.routing import APIRoute

# --- Alembic миграции ---
from alembic import command
from alembic.config import Config