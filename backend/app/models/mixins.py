"""Shared ORM helpers.

Reusable typed column helpers and a timezone-aware timestamp mixin used across
the accounting models. Money columns are declared here as ``NUMERIC(18, 2)``
mapped to Python :class:`~decimal.Decimal` — never floating point.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

# Precision/scale for every monetary column in the system.
MONEY_PRECISION = 18
MONEY_SCALE = 2


class TimestampMixin:
    """Adds a timezone-aware ``created_at`` column with a server default."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
