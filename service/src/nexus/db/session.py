"""Async engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from nexus.db.models import Base

_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> AsyncEngine:
    global _engine, _factory
    _engine = create_async_engine(database_url, future=True, pool_pre_ping=True)
    _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _factory is None:
        raise RuntimeError("init_engine() must be called before session_factory()")
    return _factory


async def create_all() -> None:
    """Development and test convenience. Deployed environments use Alembic (NX-030)."""
    if _engine is None:
        raise RuntimeError("init_engine() must be called first")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Close the connection pool. Called on shutdown and in test teardown."""
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _factory = None


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session
