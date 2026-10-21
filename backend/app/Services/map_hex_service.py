# backend/app/Services/map_hex_service.py

from Config.imports import (UUID, HTTPException, status, select, AsyncSession, UploadFile, uuid4, update, or_)
from backend.app.Database.Models.Gameplay.maps import CampaignMap, MapLayer, MapHex, Token
from backend.app.Services import lobby_service
from backend.app.Services import map_image_service
from backend.app.Services.lobby_service import (is_game_master, get_session_for_user)
from backend.app.Services import map_management_service
from backend.app.Services.hex_geometry import offset_to_axial_oddr, axial_distance, hex_line_draw


async def _get_map_and_check_master(session: AsyncSession, map_id: UUID, master_id: UUID, *, for_update: bool = False) -> CampaignMap:
	if for_update:
		statement = (
			select(CampaignMap)
			.where(CampaignMap.id == map_id)
			.with_for_update()
			.execution_options(populate_existing=True)
		)
		result = await session.execute(statement)
		campaign_map = result.scalar_one_or_none()
	else:
		campaign_map = await session.get(CampaignMap, map_id)

	if campaign_map is None:
		raise HTTPException(
			status.HTTP_404_NOT_FOUND,
			"Карта не найдена",
		)

	if not await is_game_master(
			session,
			campaign_map.game_id,
			master_id,
	):
		raise HTTPException(
			status.HTTP_403_FORBIDDEN,
			"Только мастер игры может управлять картой",
		)

	return campaign_map

async def generate_hex_grid(session: AsyncSession, map_id: UUID, master_id: UUID, rows: int, cols: int) -> MapLayer:
	"""Накладывает гекс-сетку поверх карты — работает и для image_upload, и для procedural_generation."""
	campaign_map = await _get_map_and_check_master(session, map_id, master_id, for_update=True)

	existing_stmt = select(MapLayer).where(MapLayer.map_id == campaign_map.id, MapLayer.layer_type == "vector_tiles")
	if (await session.execute(existing_stmt)).scalar_one_or_none() is not None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "На этой карте уже есть слой гексов")

	layer = MapLayer(map_id=campaign_map.id, name="Hex Grid", layer_type="vector_tiles", z_index=1)
	session.add(layer)
	await session.flush()

	hexes = []
	for row in range(rows):
		for col in range(cols):
			q, r = offset_to_axial_oddr(col, row)
			hexes.append(MapHex(
				layer_id=layer.id,
				axial_q=q,
				axial_r=r,
				h3_index=f"{row}:{col}",
				is_visible_to_players=not campaign_map.fog_of_war_enabled,
			))
	session.add_all(hexes)
	await session.commit()
	await session.refresh(layer)
	return layer

def _has_line_of_sight(origin: tuple[int, int], target: tuple[int, int],
		hex_by_coord: dict[tuple[int, int], MapHex],origin_elevation: int, target_elevation: int) -> bool:
	"""
	Упрощённая проверка видимости: блокирует только гекс с cover=true в data_json,
	если его высота не ниже обеих точек линии. Это эвристика, не точные правила 5e по укрытиям.
	"""
	for coord in hex_line_draw(origin, target):
		if coord in (origin, target):
			continue
		blocking_hex = hex_by_coord.get(coord)
		if blocking_hex is None:
			continue
		is_cover = bool((blocking_hex.data_json or {}).get("cover"))
		if is_cover and blocking_hex.elevation >= max(origin_elevation, target_elevation):
			return False
	return True

async def recalc_fog_of_war(session: AsyncSession, map_id: UUID, viewer_token_ids: list[UUID]) -> set[UUID]:
	"""Пересчитывает MapHex.is_visible_to_players/explored_by_players по токенам-наблюдателям."""
	campaign_map = (
		await session.execute(
			select(CampaignMap)
			.where(CampaignMap.id == map_id)
			.with_for_update()
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()
	if campaign_map is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Карта не найдена")

	layer_stmt = select(MapLayer).where(MapLayer.map_id == map_id, MapLayer.layer_type == "vector_tiles")
	layer = (await session.execute(layer_stmt)).scalar_one_or_none()
	if layer is None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "На карте нет слоя гексов — туман войны недоступен")

	all_hexes = list((await session.execute(select(MapHex).where(MapHex.layer_id == layer.id))).scalars().all())
	hex_by_id = {h.id: h for h in all_hexes}
	hex_by_coord = {(h.axial_q, h.axial_r): h for h in all_hexes}

	viewers_stmt = select(Token).where(Token.id.in_(viewer_token_ids), Token.current_hex_id.is_not(None))
	viewers = list((await session.execute(viewers_stmt)).scalars().all())

	visible_coords: set[tuple[int, int]] = set()
	for viewer in viewers:
		origin_hex = hex_by_id.get(viewer.current_hex_id)
		if origin_hex is None:
			continue
		origin = (origin_hex.axial_q, origin_hex.axial_r)
		for candidate in all_hexes:
			target = (candidate.axial_q, candidate.axial_r)
			if axial_distance(origin, target) > viewer.vision_radius_cells:
				continue
			if _has_line_of_sight(origin, target, hex_by_coord, origin_hex.elevation, candidate.elevation):
				visible_coords.add(target)

	for hex_row in all_hexes:
		coord = (hex_row.axial_q, hex_row.axial_r)
		hex_row.is_visible_to_players = coord in visible_coords
		if coord in visible_coords:
			hex_row.explored_by_players = True

	await session.commit()
	return {h.id for h in all_hexes if (h.axial_q, h.axial_r) in visible_coords}

async def create_map(session: AsyncSession, master_id: UUID, data: "MapCreate", *, background_image: UploadFile | None = None) -> CampaignMap:
	if not await is_game_master(session, data.game_id, master_id):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
			detail="Только мастер игры может создавать карты")

	title = data.title.strip()

	if not title:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Укажите название карты",
		)

	if data.map_type == "procedural_generation":
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=(
				"Создание процедурных карт пока не подключено. "
				"Используйте карту на основе изображения"
			),
		)

	if data.map_type != "image_upload":
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Неизвестный тип карты",
		)

	if data.session_id is not None:
		game_session = await get_session_for_user(
			session,
			data.session_id,
			master_id,
		)

		if game_session.game_id != data.game_id:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Сессия не принадлежит указанной игре",
			)

	values = data.model_dump()
	values["title"] = title
	values["grid_settings_json"] = data.grid_settings_json or {}

	map_id = uuid4()
	image_saved = False

	if background_image is not None:
		contents = await map_image_service.prepare_background(
			background_image,
		)
		await map_image_service.save_background(map_id, contents)
		image_saved = True
		values["background_image_url"] = f"/maps/{map_id}/background"

	campaign_map = CampaignMap(id=map_id, **values)

	try:
		session.add(campaign_map)
		await session.commit()
	except Exception:
		await session.rollback()

		if image_saved:
			await map_image_service.remove_background(map_id)

		raise

	# После успешного commit файл при ошибке refresh уже не удаляем:
	# запись карты сохранена.
	await session.refresh(campaign_map)
	return campaign_map

async def list_maps_for_game(session: AsyncSession, game_id: UUID) -> list[CampaignMap]:
	result = await session.execute(select(CampaignMap).where(CampaignMap.game_id == game_id))
	return list(result.scalars().all())

async def get_map(session: AsyncSession, map_id: UUID) -> CampaignMap:
	campaign_map = await session.get(CampaignMap, map_id)
	if campaign_map is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Карта не найдена")
	return campaign_map

async def update_map(session: AsyncSession, map_id: UUID, master_id: UUID, data: "MapUpdate", *, background_image: UploadFile | None = None) -> CampaignMap:
	backup_path = None
	image_replaced = False

	try:
		campaign_map = await _get_map_and_check_master(
			session,
			map_id,
			master_id,
			for_update=True,
		)

		values = data.model_dump(exclude_unset=True)

		if "title" in values:
			title = values["title"]

			if title is None or not title.strip():
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail="Укажите название карты",
				)

			values["title"] = title.strip()

		if background_image is not None:
			if campaign_map.map_type != "image_upload":
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail=(
						"Загрузка фона доступна только для карты "
						"на основе изображения"
					),
				)

			contents = await map_image_service.prepare_background(
				background_image,
			)

			backup_path = await map_image_service.replace_background(
				map_id,
				contents,
			)
			image_replaced = True

			# Адрес формируется сервером, а не берётся из имени файла.
			values["background_image_url"] = (
				f"/maps/{map_id}/background"
			)

		for field, value in values.items():
			setattr(campaign_map, field, value)

		await session.commit()

	except Exception:
		try:
			if image_replaced:
				await map_image_service.rollback_background(
					map_id,
					backup_path,
				)
		finally:
			await session.rollback()

		raise

	# Запись уже сохранена: ошибка refresh не должна
	# возвращать старое изображение.
	if image_replaced:
		await map_image_service.finish_background_replacement(
			backup_path,
		)

	await session.refresh(campaign_map)
	return campaign_map

async def set_active_map(session: AsyncSession, map_id: UUID, master_id: UUID) -> CampaignMap:
	return await map_management_service.set_map_activity(session, map_id, master_id, active=True)

async def delete_map(session: AsyncSession, map_id: UUID, master_id: UUID) -> None:
	campaign_map = await _get_map_and_check_master(session, map_id, master_id, for_update=True)

	hex_ids = (select(MapHex.id)
		.join(MapLayer, MapHex.layer_id == MapLayer.id)
		.where(MapLayer.map_id == map_id))

	try:
		await session.execute(
			update(Token)
			.where(
				or_(Token.current_map_id == map_id,
					Token.current_hex_id.in_(hex_ids))
			)
			.values(
				current_map_id=None,
				current_hex_id=None,
			)
		)

		await session.delete(campaign_map)
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	await map_image_service.remove_background(map_id)

async def _require_maps_master(session: AsyncSession, game_id: UUID, user_id: UUID) -> None:
	game = await lobby_service.get_game(
		session,
		game_id,
		user_id,
	)

	if game.master_id != user_id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Каталог карт доступен только мастеру игры",
		)