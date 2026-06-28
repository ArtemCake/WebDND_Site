# Config/imports.py

import os
import asyncio
import uvicorn
import datetime
from typing import List
from pydantic import Field
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, Integer, String, Text, DateTime, MetaData