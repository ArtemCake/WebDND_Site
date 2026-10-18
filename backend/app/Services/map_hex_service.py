# backend/app/Services/map_hex_service.py

from Config.imports import (UUID, HTTPException, status, select, AsyncSession)
from backend.app.Database.Models.Gameplay.maps import CampaignMap, MapLayer, MapHex, Token
from backend.app.Services.lobby_service import is_game_master
from backend.app.Services.hex_geometry import offset_to_axial_oddr, axial_distance, hex_line_draw


async def _get_map_and_check_master(session: AsyncSession, map_id: UUID, master_id: UUID) -> CampaignMap:
	campaign_map = await session.get(CampaignMap, map_id)
	if campaign_map is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Карта не найдена")
	if not await is_game_master(session, campaign_map.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может управлять картой")
	return campaign_map

async def generate_hex_grid(
		session: AsyncSession, map_id: UUID, master_id: UUID, rows: int, cols: int,
) -> MapLayer:
	"""Накладывает гекс-сетку поверх карты — работает и для image_upload, и для procedural_generation."""
	campaign_map = await _get_map_and_check_master(session, map_id, master_id)

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

def _has_line_of_sight(
		origin: tuple[int, int], target: tuple[int, int],
		hex_by_coord: dict[tuple[int, int], MapHex],
		origin_elevation: int, target_elevation: int,
) -> bool:
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
	campaign_map = await session.get(CampaignMap, map_id)
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

async def create_map(session: AsyncSession, master_id: UUID, data: "MapCreate") -> CampaignMap:
	if not await is_game_master(session, data.game_id, master_id):
		raise HTTPException(status.HTTP_403_FORBIDDEN, "Только мастер игры может создавать карты")

	campaign_map = CampaignMap(**data.model_dump())
	session.add(campaign_map)
	await session.commit()
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

async def update_map(session: AsyncSession, map_id: UUID, master_id: UUID, data: "MapUpdate") -> CampaignMap:
	campaign_map = await _get_map_and_check_master(session, map_id, master_id)
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(campaign_map, field, value)
	await session.commit()
	await session.refresh(campaign_map)
	return campaign_map

async def set_active_map(session: AsyncSession, map_id: UUID, master_id: UUID) -> CampaignMap:
	"""Делает карту активной в текущей игровой сессии, снимая активность с остальных карт этой игры."""
	campaign_map = await _get_map_and_check_master(session, map_id, master_id)
	others_stmt = select(CampaignMap).where(
		CampaignMap.game_id == campaign_map.game_id, CampaignMap.id != campaign_map.id
	)
	for other in (await session.execute(others_stmt)).scalars().all():
		other.is_active_in_session = False
	campaign_map.is_active_in_session = True
	await session.commit()
	await session.refresh(campaign_map)
	return campaign_map

async def delete_map(session: AsyncSession, map_id: UUID, master_id: UUID) -> None:
	campaign_map = await _get_map_and_check_master(session, map_id, master_id)
	await session.delete(campaign_map)
	await session.commit()