# Config/imports.py

import os
import enum
import base64
import pathlib
import asyncio
import uvicorn
import logging
import markdown
from typing import List
from pydantic import Field
from markupsafe import Markup
from jose import JWTError, jwt
from enum import Enum as PyEnum
from argon2 import PasswordHasher
from typing import ClassVar, Dict
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi import Form as DefaultForm
from passlib.context import CryptContext
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Enum as SQLEnum, desc
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import selectinload, declarative_base, relationship
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import (func, select, Column, Integer, cast, String, Boolean, Text, Enum,
                        Table, Float, JSON, SmallInteger, CheckConstraint,
                        LargeBinary, DateTime, ForeignKey, UniqueConstraint, delete, text, update)
from fastapi import FastAPI, Request, status, UploadFile, APIRouter, Depends, HTTPException, Form, File


