# Config/imports.py

"""
Централизованный импорт зависимостей для предотвращения циклических импортов 
и обеспечения строгой типизации во всем проекте WebDND_Site.
"""

# --- Стандартная библиотека ---
import os
import re
import ssl
import time
import base64
import argon2
import pathlib
import asyncio
import logging
import secrets
import uvicorn
from sqlalchemy.future import select
from enum import Enum, StrEnum
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Type, Union
from uuid import UUID, uuid4
from contextlib import asynccontextmanager

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
from aiosmtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- Конфигурация окружения ---
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Безопасность и аутентификация ---
from argon2 import PasswordHasher
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- Утилиты файлов и путей ---
from itsdangerous import URLSafeTimedSerializer

# --- Утилиты путей и конфигурации ---
from pathlib import Path

# --- Валидация API (Pydantic) ---
from pydantic import ValidationError  # FastAPI переименовал это из RequestValidationError внутри себя
from fastapi.exceptions import RequestValidationError

# --- Роутинг ---
from fastapi.routing import APIRoute

# --- Alembic миграции ---
from alembic import command
from alembic.config import Config