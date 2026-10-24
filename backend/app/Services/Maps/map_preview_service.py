# backend/app/Services/Maps/map_preview_service.py

from Config.imports import (AsyncSession, HTTPException, UUID, select,
	SimpleNamespace, run_in_threadpool)
from backend.app.Database.Models.Gameplay.maps import MapLayer, MapHex
from backend.app.Services.Maps import map_hex_service
from backend.app.Services.Maps.hex_geometry import (offset_to_axial_oddr, axial_distance)
from backend.app.Schemas.maps import MapPreviewIn


def _calculate(cells: list[dict], payload: MapPreviewIn) -> list[dict]:
	by_coord = {
		(cell["q"], cell["r"]): SimpleNamespace(
			elevation=cell["elevation"],
			data_json={"cover": cell["cover"]},
		)
		for cell in cells
	}

	has_q = payload.origin_q is not None
	has_r = payload.origin_r is not None

	if has_q != has_r:
		raise HTTPException(422, "Нужны обе координаты наблюдателя")

	origin = (
		(payload.origin_q, payload.origin_r)
		if has_q else None
	)

	if origin is not None and origin not in by_coord:
		raise HTTPException(422, "Наблюдатель находится вне сетки")

	for cell in cells:
		target = (cell["q"], cell["r"])
		cell["visible"] = False

		if origin is None:
			continue

		if axial_distance(origin, target) > payload.vision_radius:
			continue

		cell["visible"] = map_hex_service._has_line_of_sight(
			origin,
			target,
			by_coord,
			by_coord[origin].elevation,
			cell["elevation"],
		)

	return cells

async def preview(session: AsyncSession, user_id: UUID, payload: MapPreviewIn) -> dict:
	await map_hex_service._require_maps_master(session, payload.game_id, user_id)

	rows = payload.rows
	cols = payload.cols
	persisted_grid = False
	show_grid = True
	cells = []

	if payload.map_id is not None:
		campaign_map = await map_hex_service._get_map_and_check_master(
			session, payload.map_id, user_id,
		)

		if campaign_map.game_id != payload.game_id:
			raise HTTPException(400, "Карта принадлежит другой игре")

		settings = campaign_map.grid_settings_json or {}
		show_grid = bool(settings.get("show_grid", True))

		layer = (
			await session.execute(
				select(MapLayer).where(
					MapLayer.map_id == payload.map_id,
					MapLayer.layer_type == "vector_tiles",
					)
			)
		).scalar_one_or_none()

		if layer is not None:
			persisted_grid = True
			stored = (
				await session.execute(
					select(
						MapHex.axial_q,
						MapHex.axial_r,
						MapHex.elevation,
						MapHex.data_json,
						MapHex.explored_by_players,
					).where(MapHex.layer_id == layer.id)
				)
			).all()

			for cell in stored:
				col = (
						cell.axial_q
						+ (cell.axial_r - (cell.axial_r & 1)) // 2
				)
				cells.append({
					"q": cell.axial_q,
					"r": cell.axial_r,
					"col": col,
					"row": cell.axial_r,
					"elevation": cell.elevation,
					"cover": bool((cell.data_json or {}).get("cover")),
					"explored": cell.explored_by_players,
				})

			if cells:
				rows = max(cell["row"] for cell in cells) + 1
				cols = max(cell["col"] for cell in cells) + 1

	if not persisted_grid:
		for row in range(rows):
			for col in range(cols):
				q, r = offset_to_axial_oddr(col, row)
				cells.append({
					"q": q,
					"r": r,
					"col": col,
					"row": row,
					"elevation": 0,
					"cover": False,
					"explored": False,
				})

	cells = await run_in_threadpool(_calculate, cells, payload)

	return {
		"rows": rows,
		"cols": cols,
		"show_grid": show_grid,
		"persisted_grid": persisted_grid,
		"hexes": cells,
	}