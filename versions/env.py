# versions/env.py

import asyncio
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
from app.database.database import Base
from Config.Config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Создаём синхронный движок для миграций
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True  # если используете схемы
        )

        with context.begin_transaction():
            context.run_migrations()

# Основной блок выполнения
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()