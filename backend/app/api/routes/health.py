"""Health-check route.

Liveness endpoint kept deliberately independent of the database so platform
health checks and the frontend connectivity probe succeed even when no DB is
configured (as during the scaffold phase).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return service liveness. Does not require a database connection."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.service_name)
