"""Pydantic response schema for the health endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for ``GET /health``."""

    status: str
    service: str
