# backend/app/Routers/api.py

from Config.imports import APIRouter


router = APIRouter(
	prefix="/auth",
	tags=["auth"],
)