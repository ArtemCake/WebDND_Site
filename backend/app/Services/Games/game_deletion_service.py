# backend/app/Services/Games/game_deletion_service.py

from Config.imports import (AsyncSession, UUID, HTTPException, select, delete, or_,
	logging, run_in_threadpool, asyncio)
from backend.app.Database.Models.Core.user import User
from backend.app.Database.Models.Gameplay.lobby import (Game, Party, Session as GameSession, DiceRoll, GameDeletionJob)
from backend.app.Database.Models.Gameplay.maps import CampaignMap
from backend.app.Services.Maps import map_cleanup_service


log = logging.getLogger(__name__)

async def _finish_cleanup(session: AsyncSession, game_id: UUID, master_id: UUID) -> dict:
	try:
		job = (
			await session.execute(
				select(GameDeletionJob)
				.where(GameDeletionJob.game_id == game_id)
				.with_for_update()
				.execution_options(populate_existing=True)
			)
		).scalar_one_or_none()

		if job is None:
			raise HTTPException(404, "Задание удаления не найдено")

		if job.master_id != master_id:
			raise HTTPException(
				403,
				"Только мастер удалённой игры может повторить очистку",
			)

		if not job.cleanup_complete:
			try:
				await run_in_threadpool(
					map_cleanup_service.execute_plan,
					job.cleanup_plan,
				)
			except (OSError, ValueError, RuntimeError):
				log.exception(
					"Не завершена очистка карт удалённой игры %s",
					game_id,
				)
				await session.rollback()

				return {
					"deleted": True,
					"cleanup_complete": False,
					"detail": (
						"Игра удалена из базы данных, но очистка "
						"файлов ещё не завершена. Можно повторить "
						"очистку; сервер также будет повторять её."
					),
				}

			job.cleanup_complete = True

		await session.commit()

	except Exception:
		await session.rollback()
		raise

	return {
		"deleted": True,
		"cleanup_complete": True,
		"detail": "Игра, её карты и каталог карт удалены.",
	}

async def delete_game(session: AsyncSession, game_id: UUID, master_id: UUID) -> dict:
	try:
		# Выбираем поля, не загружая отношения Game.
		game = (
			await session.execute(
				select(
					Game.id,
					Game.master_id,
					Game.maps_storage_folder,
				)
				.where(Game.id == game_id)
				.with_for_update()
			)
		).one_or_none()

		if game is not None:
			if game.master_id != master_id:
				raise HTTPException(
					403,
					"Только мастер игры может удалить её",
				)

			# Порядок блокировок: игра, затем карты.
			maps = (
				await session.execute(
					select(
						CampaignMap.id,
						CampaignMap.background_storage_path,
					)
					.where(CampaignMap.game_id == game_id)
					.order_by(CampaignMap.id)
					.with_for_update()
				)
			).all()

			master_folder = (
				await session.execute(
					select(User.maps_storage_folder)
					.where(User.id == master_id)
				)
			).scalar_one_or_none()

			try:
				plan = map_cleanup_service.build_plan(
					game_id,
					master_id,
					master_folder,
					game.maps_storage_folder,
					maps,
				)
			except (ValueError, RuntimeError) as exc:
				log.exception(
					"Не удалось подготовить очистку игры %s",
					game_id,
				)
				raise HTTPException(
					409,
					"Не удалось безопасно определить каталог карт. "
					"Игра не удалена; требуется проверка хранилища.",
				) from exc

			# Не очищаем каталог, на который ссылаются карты
			# другой игры, даже при повреждённых данных.
			for relative in plan["directories"]:
				shared_map = (
					await session.execute(
						select(CampaignMap.id)
						.where(
							CampaignMap.game_id != game_id,
							CampaignMap.background_storage_path.startswith(
								f"{relative}/",
								autoescape=True,
							),
							)
						.limit(1)
					)
				).scalar_one_or_none()

				if shared_map is not None:
					raise HTTPException(
						409,
						"Каталог используется картами другой игры. "
						"Удаление остановлено.",
					)

			session.add(
				GameDeletionJob(
					game_id=game_id,
					master_id=master_id,
					cleanup_plan=plan,
					cleanup_complete=False,
				)
			)

			session_ids = select(GameSession.id).where(
				GameSession.game_id == game_id
			)
			party_ids = select(Party.id).where(
				Party.game_id == game_id
			)

			# В текущей модели у бросков SET NULL.
			# Для окончательного удаления истории игры
			# удаляем её броски явно.
			await session.execute(
				delete(DiceRoll)
				.where(
					or_(
						DiceRoll.session_id.in_(session_ids),
						DiceRoll.party_id.in_(party_ids),
					)
				)
				.execution_options(synchronize_session=False)
			)

			# Core DELETE: используем каскады самой БД,
			# не ORM-обнуление обязательных внешних ключей.
			await session.execute(
				delete(Game)
				.where(Game.id == game_id)
				.execution_options(synchronize_session=False)
			)

			# Задание и удаление записей фиксируются вместе.
			# До этого момента файлы не изменялись.
			await session.commit()

	except Exception:
		await session.rollback()
		raise

	# Если игра уже удалена, повторный запрос продолжает
	# сохранённое задание с отдельной проверкой владельца.
	return await _finish_cleanup(session, game_id, master_id)

async def run_cleanup_worker(session_factory) -> None:
	while True:
		try:
			async with session_factory() as session:
				pending = (
					await session.execute(
						select(
							GameDeletionJob.game_id,
							GameDeletionJob.master_id,
						)
						.where(
							GameDeletionJob.cleanup_complete.is_(False)
						)
						.order_by(GameDeletionJob.created_at)
						.limit(100)
					)
				).all()

			for item in pending:
				try:
					async with session_factory() as session:
						await _finish_cleanup(
							session,
							item.game_id,
							item.master_id,
						)
				except Exception:
					log.exception(
						"Ошибка повторной очистки игры %s",
						item.game_id,
					)

		except Exception:
			log.exception("Ошибка обработки заданий очистки игр")

		await asyncio.sleep(60)