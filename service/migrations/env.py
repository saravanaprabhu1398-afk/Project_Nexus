"""Alembic environment (NX-030).

Two deliberate choices:

* the URL comes from NEXUS_DATABASE_URL via the application settings, so
  migrations and the service can never disagree about which database they mean,
  and no connection string is committed;
* `render_as_batch` is on so SQLite (used for local development and tests) can
  emulate the ALTER statements it does not support natively - without it, the
  first column change would pass in CI and fail on a developer machine.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from nexus.config import get_settings
from nexus.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic's Config hands back this placeholder when the ini omits the option,
# so "unset" has to be tested for explicitly - a plain falsiness check silently
# leaves the placeholder in place and every CLI invocation then tries to connect
# to it.
_PLACEHOLDER_URL = "driver://user:pass@localhost/dbname"

# A caller may set the URL explicitly (tests do). Otherwise it comes from the
# same settings object the service uses, so the two can never disagree.
_configured = config.get_main_option("sqlalchemy.url", None)
if not _configured or _configured == _PLACEHOLDER_URL:
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def _configure(connection: Connection | None = None, url: str | None = None) -> None:
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        literal_binds=url is not None,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )


def run_migrations_offline() -> None:
    _configure(url=config.get_main_option("sqlalchemy.url"))
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
