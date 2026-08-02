# Config/imports.py

import os
import sys
import enum
import base64
import pathlib
import asyncio
import uvicorn
import logging
import markdown
from markupsafe import Markup
from jose import JWTError, jwt
from enum import Enum as PyEnum
from argon2 import PasswordHasher
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from sqlalchemy.types import SchemaType
from fastapi import Form as DefaultForm
from passlib.context import CryptContext
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Enum as SQLEnum, desc
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from concurrent.futures import ThreadPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pydantic import Field, BaseModel, conint, confloat
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from typing import List, Optional, Any, Dict, ClassVar, Type
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import (func, select, Column, Integer, cast, String, Boolean, Text, Enum, Table,
                        Float, JSON, SmallInteger, CheckConstraint, LargeBinary, DateTime, ForeignKey,
                        UniqueConstraint, delete, text, update, Index, and_, or_)
from fastapi import FastAPI, Request, status, UploadFile, APIRouter, Depends, HTTPException, Form, File
from sqlalchemy.orm import selectinload, declarative_base, relationship, Mapped, mapped_column, backref, foreign, remote