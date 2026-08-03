"""Async database engine and session foundation (SQLAlchemy 2).

The engine and session factory are created lazily so the application — and the
``GET /health`` endpoint in particular — can start without a live database
connection during the scaffold phase. ``get_session`` is a FastAPI dependency
that yields an ``AsyncSession``; it is unused until accounting routes exist.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use.

    Raises:
        RuntimeError: if ``DATABASE_URL`` is not configured.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured; a database connection is "
                "required for this operation."
            )
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, creating it on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an ``AsyncSession`` and closes it."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
