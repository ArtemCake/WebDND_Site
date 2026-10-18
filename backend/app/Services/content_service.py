# backend/app/Services/content_service.py

from Config.imports import (AsyncSession, select)
from backend.app.Database.Models.Content.game_systems import GameSystem


async def list_active_systems(session: AsyncSession) -> list[GameSystem]:
	result = await session.execute(
		select(GameSystem)
		.where(GameSystem.is_active.is_(True))
		.order_by(GameSystem.name)
	)
	return list(result.scalars().all())