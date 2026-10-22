# backend/app/Services/Maps/map_management_service.py

from Config.imports import (AsyncSession, UUID, HTTPException, select, update,
	or_, uuid4, deepcopy)
from backend.app.Database.Models.Gameplay.lobby import Game
from backend.app.Database.Models.Gameplay.maps import (CampaignMap, MapLayer, MapHex, Token, MapObject, SpatialAudioZone)
from backend.app.Services.Maps import map_image_service, map_storage_service


async def list_target_games(session: AsyncSession, master_id: UUID, source_game_id: UUID) -> list[Game]:
	result = await session.execute(
		select(Game)
		.where(
			Game.master_id == master_id,
			Game.id != source_game_id,
			)
		.order_by(Game.title, Game.id)
	)
	return list(result.scalars().all())

async def _lock_context(session: AsyncSession, map_id: UUID,	master_id: UUID, *,
		target_game_id: UUID | None = None,
		expected_game_id: UUID | None = None) -> CampaignMap:
	source_game_id = (
		await session.execute(
			select(CampaignMap.game_id)
			.where(CampaignMap.id == map_id)
		)
	).scalar_one_or_none()

	if source_game_id is None:
		raise HTTPException(404, "Карта не найдена")

	if (
			expected_game_id is not None
			and source_game_id != expected_game_id
	):
		raise HTTPException(
			409,
			"Карта уже находится в другой игре. Обновите страницу",
		)

	if target_game_id == source_game_id:
		raise HTTPException(400, "Выберите другую игру")

	game_ids = {source_game_id}
	if target_game_id is not None:
		game_ids.add(target_game_id)

	# Сначала игры в едином порядке, затем карта.
	# Нельзя сначала захватить разные карты одной игры,
	# а потом ждать друг друга при переключении активности.
	result = await session.execute(
		select(Game)
		.where(Game.id.in_(game_ids))
		.order_by(Game.id)
		.with_for_update()
		.execution_options(populate_existing=True)
	)
	games = {
		game.id: game
		for game in result.scalars().all()
	}

	for game_id in game_ids:
		game = games.get(game_id)

		if game is None:
			raise HTTPException(404, "Игра не найдена")

		if game.master_id != master_id:
			raise HTTPException(
				403,
				"Для операции нужны права мастера "
				"в исходной и целевой игре",
			)

	campaign_map = (
		await session.execute(
			select(CampaignMap)
			.where(CampaignMap.id == map_id)
			.with_for_update()
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()

	if campaign_map is None:
		raise HTTPException(404, "Карта не найдена")

	# Пока ожидали блокировку, другой запрос мог перенести карту.
	if campaign_map.game_id != source_game_id:
		raise HTTPException(
			409,
			"Принадлежность карты изменилась. Обновите страницу",
		)

	return campaign_map

async def set_map_activity(session: AsyncSession, map_id: UUID, master_id: UUID, *, active: bool) -> CampaignMap:
	try:
		campaign_map = await _lock_context(
			session, map_id, master_id,
		)

		if active:
			await session.execute(
				update(CampaignMap)
				.where(
					CampaignMap.game_id == campaign_map.game_id,
					CampaignMap.id != map_id,
					CampaignMap.is_active_in_session.is_(True),
					)
				.values(is_active_in_session=False)
			)

		campaign_map.is_active_in_session = active
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	await session.refresh(campaign_map)
	return campaign_map

async def _check_move_dependencies(session: AsyncSession, map_id: UUID) -> None:
	layer_ids = (
		select(MapLayer.id)
		.where(MapLayer.map_id == map_id)
	)
	hex_ids = (
		select(MapHex.id)
		.where(MapHex.layer_id.in_(layer_ids))
	)

	token_id = (
		await session.execute(
			select(Token.id)
			.where(
				or_(
					Token.current_map_id == map_id,
					Token.current_hex_id.in_(hex_ids),
					)
			)
			.limit(1)
		)
	).scalar_one_or_none()

	if token_id is not None:
		raise HTTPException(
			409,
			"Перенос невозможен: к карте или её гексам "
			"привязаны токены. Сначала снимите привязки "
			"либо воспользуйтесь копированием",
		)

	object_id = (
		await session.execute(
			select(MapObject.id)
			.where(MapObject.layer_id.in_(layer_ids))
			.limit(1)
		)
	).scalar_one_or_none()

	if object_id is not None:
		raise HTTPException(
			409,
			"Перенос карты с объектами пока не поддерживается. "
			"Объекты не удалены. Можно скопировать основу карты",
		)

	audio_id = (
		await session.execute(
			select(SpatialAudioZone.id)
			.where(SpatialAudioZone.map_id == map_id)
			.limit(1)
		)
	).scalar_one_or_none()

	if audio_id is not None:
		raise HTTPException(
			409,
			"Перенос карты с аудиозонами пока не поддерживается. "
			"Аудиозоны не удалены. Можно скопировать основу карты",
		)

async def move_map(session: AsyncSession, map_id: UUID, master_id: UUID, source_game_id: UUID, target_game_id: UUID) -> CampaignMap:
	old_key = None
	new_path = None
	image_saved = False

	try:
		campaign_map = await _lock_context(
			session,
			map_id,
			master_id,
			target_game_id=target_game_id,
			expected_game_id=source_game_id,
		)

		await _check_move_dependencies(session, map_id)

		old_key = map_storage_service.image_key(campaign_map)
		contents = None

		if campaign_map.background_image_url == (
				f"/maps/{campaign_map.id}/background"
		):
			contents = await map_image_service.read_background(
				old_key,
			)

		number, new_path = (
			await map_storage_service.allocate_location(
				session,
				target_game_id,
				master_id,
			)
		)

		if contents is not None:
			await map_image_service.save_background(
				new_path,
				contents,
			)
			image_saved = True

			written = await map_image_service.read_background(
				new_path,
			)
			if written != contents:
				raise HTTPException(
					500,
					"Не удалось проверить изображение после переноса",
				)

		campaign_map.game_id = target_game_id
		campaign_map.map_number = number
		campaign_map.background_storage_path = new_path
		campaign_map.session_id = None
		campaign_map.is_active_in_session = False

		await session.commit()

	except Exception:
		try:
			await session.rollback()
		finally:
			if image_saved:
				await map_image_service.remove_background(
					new_path,
				)
		raise

	if image_saved:
		await map_image_service.remove_background(old_key)

	await session.refresh(campaign_map)
	return campaign_map

async def _copy_layers(session: AsyncSession, source_map_id: UUID, destination: CampaignMap) -> None:
	layers = list((
		              await session.execute(
			              select(MapLayer)
			              .where(MapLayer.map_id == source_map_id)
			              .order_by(MapLayer.z_index, MapLayer.id)
		              )
	              ).scalars().all())

	for source_layer in layers:
		layer = MapLayer(
			id=uuid4(),
			map_id=destination.id,
			name=source_layer.name,
			z_index=source_layer.z_index,
			opacity=source_layer.opacity,
			is_visible=source_layer.is_visible,
			layer_type=source_layer.layer_type,
			data_json=deepcopy(source_layer.data_json),
		)
		session.add(layer)
		await session.flush()

		hexes = (
			await session.execute(
				select(MapHex)
				.where(MapHex.layer_id == source_layer.id)
				.order_by(MapHex.id)
			)
		).scalars().all()

		# Сохраняем геометрию и параметры местности,
		# но не историю исследования исходной игры.
		for start in range(0, len(hexes), 500):
			session.add_all([
				MapHex(
					id=uuid4(),
					layer_id=layer.id,
					axial_q=source_hex.axial_q,
					axial_r=source_hex.axial_r,
					h3_index=source_hex.h3_index,
					terrain_type_id=source_hex.terrain_type_id,
					elevation=source_hex.elevation,
					is_visible_to_players=(
						not destination.fog_of_war_enabled
					),
					explored_by_players=False,
					data_json=deepcopy(source_hex.data_json),
				)
				for source_hex in hexes[start:start + 500]
			])
			await session.flush()

async def copy_map(session: AsyncSession, map_id: UUID, master_id: UUID, source_game_id: UUID, target_game_id: UUID) -> CampaignMap:
	new_map_id = uuid4()
	new_path = None
	image_saved = False

	try:
		source = await _lock_context(
			session,
			map_id,
			master_id,
			target_game_id=target_game_id,
			expected_game_id=source_game_id,
		)

		contents = None

		if source.background_image_url:
			if source.background_image_url != (
					f"/maps/{source.id}/background"
			):
				raise HTTPException(
					409,
					"Карта использует фон по произвольному адресу. "
					"Сначала загрузите изображение через "
					"редактирование карты",
				)

			contents = await map_image_service.read_background(
				map_storage_service.image_key(source),
			)

		number, new_path = (
			await map_storage_service.allocate_location(
				session,
				target_game_id,
				master_id,
			)
		)

		background_url = None

		if contents is not None:
			await map_image_service.save_background(
				new_path,
				contents,
			)
			image_saved = True
			background_url = f"/maps/{new_map_id}/background"

		destination = CampaignMap(
			id=new_map_id,
			game_id=target_game_id,
			session_id=None,
			map_number=number,
			background_storage_path=new_path,
			title=source.title,
			map_type=source.map_type,
			background_image_url=background_url,
			grid_settings_json=deepcopy(source.grid_settings_json),
			fog_of_war_enabled=source.fog_of_war_enabled,
			lighting_model=source.lighting_model,
			is_active_in_session=False,
		)
		session.add(destination)
		await session.flush()

		await _copy_layers(session, source.id, destination)
		await session.commit()

	except Exception:
		try:
			await session.rollback()
		finally:
			if image_saved:
				await map_image_service.remove_background(
					new_path,
				)
		raise

	await session.refresh(destination)
	return destination