# app/Routers/main.py

from Config.imports import (APIRouter)


router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)
