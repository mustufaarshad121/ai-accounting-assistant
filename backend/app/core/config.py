"""Application configuration via Pydantic settings.

All configuration is read from environment variables (or a local ``.env``
file, which is git-ignored and must never contain committed secrets). Values
are referenced by name only; secret values are never logged.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application metadata ---
    app_name: str = "AI-Powered Accounting Assistant API"
    service_name: str = "ai-accounting-assistant-api"
    app_version: str = "0.1.0"
    environment: str = "development"

    # --- Database ---
    # Pooled async URL used by the FastAPI app at runtime (postgresql+asyncpg://...).
    # Optional during the scaffold phase so the app boots without a database.
    database_url: str | None = None
    # Direct (non-pooled) URL used by Alembic migrations.
    direct_database_url: str | None = None

    # --- CORS ---
    # Origin of the frontend allowed to call this API.
    frontend_url: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins derived from ``frontend_url``."""
        return [self.frontend_url]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
