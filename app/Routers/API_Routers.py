# app/Routers/API_Routers.py

from Config.imports import (APIRouter)


router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)
