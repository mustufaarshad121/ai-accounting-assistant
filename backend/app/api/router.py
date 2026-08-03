"""Versioned API router aggregator.

Collects every ``/api/v1`` feature router into one router that ``main.py`` mounts
under the ``/api/v1`` prefix. Feature branches append their routers here; the
health route stays outside this prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import accounts, entries

api_router = APIRouter()
api_router.include_router(accounts.router)
api_router.include_router(entries.router)
