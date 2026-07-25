# app/services/log_service.py

from Config.imports import logging
from app.database._models import UserLog, AppLog
from app.database.session import get_async_logs_db
from app.enums.log_enums import LogAction, LogLevelEnum

logger = logging.getLogger(__name__)

class LogService:
	"""
	Сервис для записи системных логов в отдельную базу данных.
	"""

	@staticmethod
	async def _create_log_entry(session, log_model, **log_data):
		"""Вспомогательный метод для создания записи лога."""
		try:
			new_log = log_model(**log_data)
			session.add(new_log)
			await session.commit()
			return new_log.id
		except Exception as e:
			logger.error(
				f"Ошибка создания записи лога ({log_model.__name__}): {e}",
				exc_info=True
			)
			raise

	@staticmethod
	async def create_log(
			username: str | None,
			action: LogAction = LogAction.ACTION_NONE,
			description: str | None = None,
			log_level: LogLevelEnum = LogLevelEnum.INFO
	) -> bool:
		"""Создаёт запись в журнале системных логов."""
		db_manager = get_async_logs_db()
		async with (db_manager as db):
			try:
				log_id = await LogService._create_log_entry(
					db,
					AppLog,
					username=username,
					action=action,
					description=description,
					log_level=log_level
				)
				if log_id:
					logger.info(f"Системный лог создан: {action}")
					return True
				return False
			except Exception as e:
				logger.error(f"❌ Ошибка записи системного лога в БД: {e}")
				return False
			finally:
				await db.close()

	@staticmethod
	async def create_user_log(
			user_id: int,
			action: LogAction = LogAction.ACTION_NONE,
			description: str | None = None,
			log_level: LogLevelEnum = LogLevelEnum.INFO
	) -> bool:
		"""Создаёт новую запись в журнале пользовательских логов."""
		db_manager = get_async_logs_db()
		async with (db_manager as db):
			try:
				try:
					log_id = await LogService._create_log_entry(
						db,
						UserLog,
						user_id=user_id,
						action=action,
						description=description,
						log_level=log_level
					)
					if log_id:
						logger.info(f"Пользовательский лог создан для user_id={user_id}: {action}")
						return True
					return False
				finally:
					await db.close()
			except Exception as e:
				# Логируем ошибку системного лога отдельно
				try:
					await LogService.create_log(
						username=None,
						action=LogAction.LOGS_SAVE_ERROR,
						description=f"❌ Ошибка записи пользовательского лога: {e}",
						log_level=LogLevelEnum.ERROR
					)
				except Exception as log_error:
					logger.critical(
						f"Критическая ошибка: не удалось записать ошибку лога: {log_error}"
					)
					return False
