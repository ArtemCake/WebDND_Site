# Config/imports.py

import os
import base64
import pathlib
import asyncio
import uvicorn
import datetime
from typing import List
from pydantic import Field
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import declarative_base
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import (func, select, Column, Integer, cast, String, Boolean, Text,
                        LargeBinary, DateTime, ForeignKey, UniqueConstraint, delete, text, update)
from fastapi import FastAPI, Request, status, UploadFile, APIRouter, Depends, HTTPException, Form, File