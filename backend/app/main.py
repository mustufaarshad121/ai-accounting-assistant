"""FastAPI application entrypoint.

Builds the app, configures CORS from ``FRONTEND_URL``, registers structured
error handlers, and mounts the health route. Business logic lives in services
(added in feature branches), never here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Liveness endpoint (no /api/v1 prefix, no DB dependency).
    app.include_router(health.router)

    # Versioned API router is mounted in later feature branches:
    #   app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
