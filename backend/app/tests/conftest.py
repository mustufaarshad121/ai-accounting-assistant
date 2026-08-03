"""Pytest fixtures for the accounting-core service tests.

Spins up an in-memory SQLite database (shared across the test's sessions via a
``StaticPool``) and creates the schema from ``Base.metadata``. This is a logic
harness only — see ``app/tests/__init__.py`` for the PostgreSQL coverage caveat.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.db.base import Base
from app.db.seed import seed_accounts
from app.models.account import Account


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` bound to a fresh in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as sess:
        yield sess

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(session: AsyncSession) -> AsyncSession:
    """Session with the 18 default accounts seeded and committed."""
    await seed_accounts(session)
    await session.commit()
    return session


async def account_id(session: AsyncSession, code: str) -> uuid.UUID:
    """Look up a seeded account's id by its code (test helper)."""
    from sqlalchemy import select

    result = await session.execute(select(Account.id).where(Account.code == code))
    found = result.scalar_one_or_none()
    assert found is not None, f"account {code} not seeded"
    return found
