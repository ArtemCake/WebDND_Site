# backend/app/Services/content_service.py

from Config.imports import (AsyncSession, HTTPException, IntegrityError, Optional,
	UUID, or_, select, status)
from backend.app.Database.Models.Content.game_systems import GameSystem
from backend.app.Schemas.content import (GameSystemCreate,	GameSystemUpdate)


async def list_active_systems(
		session: AsyncSession,
) -> list[GameSystem]:
	result = await session.execute(
		select(GameSystem)
		.where(GameSystem.is_active.is_(True))
		.order_by(GameSystem.name)
	)
	return list(result.scalars().all())

async def list_all_systems(
		session: AsyncSession,
) -> list[GameSystem]:
	result = await session.execute(
		select(GameSystem)
		.order_by(
			GameSystem.is_active.desc(),
			GameSystem.name,
			GameSystem.id,
		)
	)
	return list(result.scalars().all())

async def get_game_system(
		session: AsyncSession,
		system_id: UUID,
) -> GameSystem:
	system = await session.get(GameSystem, system_id)

	if system is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Игровая система не найдена",
		)

	return system

async def _check_system_unique(
		session: AsyncSession,
		name: str,
		slug: str,
		exclude_id: Optional[UUID] = None,
) -> None:
	stmt = select(GameSystem.id).where(
		or_(
			GameSystem.name == name,
			GameSystem.slug == slug,
			)
	)

	if exclude_id is not None:
		stmt = stmt.where(GameSystem.id != exclude_id)

	result = await session.execute(stmt.limit(1))

	if result.scalar_one_or_none() is not None:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=(
				"Игровая система с таким названием "
				"или slug уже существует"
			),
		)

async def _commit_system(
		session: AsyncSession,
		system: GameSystem,
) -> GameSystem:
	try:
		await session.commit()
	except IntegrityError as exc:
		await session.rollback()

		# Предварительная проверка не исключает одновременные
		# запросы. Окончательную уникальность обеспечивает БД.
		sqlstate = (
				getattr(exc.orig, "sqlstate", None)
				or getattr(exc.orig, "pgcode", None)
		)

		if sqlstate == "23505":
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=(
					"Игровая система с таким названием "
					"или slug уже существует"
				),
			) from exc

		# Другие нарушения ограничений не маскируем
		# сообщением о дубликате.
		raise

	await session.refresh(system)
	return system

async def create_game_system(
		session: AsyncSession,
		data: GameSystemCreate,
) -> GameSystem:
	await _check_system_unique(
		session,
		name=data.name,
		slug=data.slug,
	)

	system = GameSystem(**data.model_dump())
	session.add(system)

	return await _commit_system(session, system)

async def update_game_system(
		session: AsyncSession,
		system_id: UUID,
		data: GameSystemUpdate,
) -> GameSystem:
	system = await get_game_system(session, system_id)
	changes = data.model_dump(exclude_unset=True)

	if not changes:
		return system

	if "name" in changes or "slug" in changes:
		await _check_system_unique(
			session,
			name=changes.get("name", system.name),
			slug=changes.get("slug", system.slug),
			exclude_id=system.id,
		)

	for field, value in changes.items():
		setattr(system, field, value)

	return await _commit_system(session, system)