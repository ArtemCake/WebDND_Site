# app/database/session.py

from Config.imports import asynccontextmanager, SQLAlchemyError
from app.database.database import AsyncSessionLocal, AsyncSessionLogsLocal


# Эта функция будет "зависимостью" (dependency) в FastAPI.
def create_db_dependency(session_local):
    """
    Фабрика для создания зависимостей БД.
    """
    @asynccontextmanager
    async def dependency():
        db = session_local()
        try:
            yield db
        except SQLAlchemyError as error:
            await db.rollback()
            raise
        except Exception as error:
            raise
        finally:
            try:
                await db.close()
            except Exception as close_error:
                raise

    return dependency

# Создаём зависимости через фабрику
get_async_db = create_db_dependency(AsyncSessionLocal)
get_async_logs_db = create_db_dependency(AsyncSessionLogsLocal)
get_async_session_factory = create_db_dependency(AsyncSessionLocal)