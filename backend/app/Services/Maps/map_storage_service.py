# backend/app/Services/Maps/map_storage_service.py

from Config.imports import (AsyncSession, UUID, HTTPException, select, update, re)
from backend.app.Database.Models.Core.user import User
from backend.app.Database.Models.Gameplay.lobby import Game


def _folder_name(prefix: str, label: str, entity_id: UUID) -> str:
	# Оставляем буквы, цифры, подчёркивания и дефисы.
	# Префикс защищает в том числе от специальных имён Windows.
	slug = re.sub(
		r"[^\w-]+",
		"-",
		(label or "").strip().lower(),
	).strip("-_")[:40].rstrip("-_")

	return f"{prefix}-{slug or 'unnamed'}-{entity_id}"

async def allocate_location(session: AsyncSession, game_id: UUID, master_id: UUID, *, number: int | None = None) -> tuple[int, str]:
	"""
	Вызывает только серверный код.

	Для новых карт number не передаётся.
	Для перевода старых данных допустимо сохранить уже назначенный номер.

	Порядок блокировок: игра, затем пользователь.
	Если операция затрагивает несколько игр, вызывающая сторона
	сначала блокирует все эти игры в порядке их идентификаторов.
	"""
	game = (
		await session.execute(
			select(Game)
			.where(Game.id == game_id)
			.with_for_update(of=Game)
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()

	if game is None:
		raise HTTPException(404, "Игра не найдена")

	if game.master_id != master_id:
		raise HTTPException(
			403,
			"Только мастер игры может сохранять её карты",
		)

	# Выбираем отдельные поля, чтобы не загружать отношения User.
	master = (
		await session.execute(
			select(
				User.id,
				User.nickname,
				User.maps_storage_folder,
			)
			.where(User.id == master_id)
			.with_for_update()
		)
	).one_or_none()

	if master is None:
		raise HTTPException(404, "Мастер игры не найден")

	master_folder = master.maps_storage_folder

	if not master_folder:
		master_folder = _folder_name(
			"master",
			master.nickname,
			master.id,
		)
		await session.execute(
			update(User)
			.where(User.id == master.id)
			.values(maps_storage_folder=master_folder)
		)

	if not game.maps_storage_folder:
		game.maps_storage_folder = _folder_name(
			"game",
			game.title,
			game.id,
		)

	next_number = game.next_map_number

	if next_number < 1:
		raise HTTPException(
			409,
			"Некорректный счётчик карт игры",
		)

	if number is None:
		number = next_number
	elif number < 1:
		raise HTTPException(409, "Некорректный номер карты")

	game.next_map_number = max(next_number, number + 1)

	path = (
		f"{master_folder}/"
		f"{game.maps_storage_folder}/"
		f"map-{number}.png"
	)

	# Сохраняем изменения внутри текущей транзакции,
	# но commit остаётся за вызывающей операцией.
	await session.flush()

	return number, path

def image_key(campaign_map) -> UUID | str:
	"""
	Новые карты используют относительный путь.
	Старые до переноса продолжают читаться по UUID.
	"""
	return (
			campaign_map.background_storage_path
			or campaign_map.id
	)