# backend/app/Services/GameSystems/registry.py

from Config.imports import (HTTPException, status)
from backend.app.Services.GameSystems.i_system import ISystem
from backend.app.Services.GameSystems.dnd5e_system import Dnd5eSystem


_SYSTEMS: dict[str, ISystem] = {
	Dnd5eSystem.slug: Dnd5eSystem(),
}

def get_system(slug: str) -> ISystem:
	"""Возвращает реализацию ISystem по slug игровой системы (GameSystem.slug)."""
	system = _SYSTEMS.get(slug)
	if system is None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Игровая система '{slug}' не поддерживается")
	return system
