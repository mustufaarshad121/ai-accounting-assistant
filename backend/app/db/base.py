"""SQLAlchemy 2 declarative base.

Defines the shared ``Base`` that ORM models will inherit from in later feature
branches. No accounting models exist yet in the scaffold phase.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models (populated in feature branches)."""
