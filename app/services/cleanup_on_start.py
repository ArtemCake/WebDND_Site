# app/services/cleanup_on_start.py

from Config.imports import datetime, timedelta, delete
from app.database.session import get_async_logs_db
from app.database._models import UserLog, LogLevelEnum
from app.services.log_service import LogService
from app.enums.log_enums import LogAction
import logging


logger = logging.getLogger(__name__)

async def cleanup_old_logs():
    """Удаляет логи старше 1 месяца при запуске приложения."""
    db = None
    try:
        db_manager = get_async_logs_db()
        async with (db_manager as db):
            await LogService.create_log(
                username=None,
                action=LogAction.LOGS_CLEAR,
                description="🧹 Запуск очистки логов старше 30 дней...",
                log_level=LogLevelEnum.INFO
            )

            one_month_ago = datetime.utcnow() - timedelta(days=30)
            stmt = delete(UserLog).where(UserLog.created_at < one_month_ago)
            result = await db.execute(stmt)
            deleted_count = result.rowcount

            await db.commit()

            if deleted_count > 0:
                await LogService.create_log(
                    username=None,
                    action=LogAction.LOGS_CLEAR,
                    description=f"✅ Удалено {deleted_count} старых записей из логов.",
                    log_level=LogLevelEnum.INFO
                )
            else:
                await LogService.create_log(
                    username=None,
                    action=LogAction.LOGS_CLEAR,
                    description="✅ Старых логов для удаления не найдено.",
                    log_level=LogLevelEnum.INFO
                )
    except Exception as e:
        print(f"❌ Ошибка при очистке старых логов: {e}")
        await LogService.create_log(
            username=None,
            action=LogAction.LOGS_CLEAR_ERROR,
            description=f"❌ Ошибка очистки логов: {e}",
            log_level=LogLevelEnum.ERROR
        )
    finally:
        if db is not None:  # Проверяем, была ли создана сессия
            await db.close()