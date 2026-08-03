"""Alembic environment.

Reads the database URL from ``DIRECT_DATABASE_URL`` (the direct, non-pooled
connection used for migrations) and targets ``Base.metadata`` for autogenerate.

No migration revisions exist during the scaffold phase; the initial revision is
created in the accounting-core feature branch. Running Alembic without a
configured ``DIRECT_DATABASE_URL`` raises a clear error rather than guessing.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings

# Import the shared metadata. Models are registered on Base.metadata in later
# feature branches; importing here keeps autogenerate wired up in advance.
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    settings = get_settings()
    url = settings.direct_database_url
    if not url:
        raise RuntimeError(
            "DIRECT_DATABASE_URL is not set. Configure it before running "
            "Alembic migrations."
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI connection)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
