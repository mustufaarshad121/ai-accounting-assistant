"""Shared Pydantic schema types.

Defines the monetary types used across request/response models and the
structured error envelope. Money is always :class:`~decimal.Decimal` — never
float — constrained to ``NUMERIC(18, 2)`` bounds and serialized to JSON as a
decimal string (e.g. ``"50000.00"``) so no binary-float rounding leaks out.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

# Input amount for a transaction: strictly positive, 2 dp, fits NUMERIC(18,2).
PositiveMoney = Annotated[
    Decimal,
    Field(gt=0, max_digits=18, decimal_places=2),
]

# Output money (a line's debit/credit): non-negative, serialized as a string.
MoneyOut = Annotated[
    Decimal,
    Field(ge=0, max_digits=18, decimal_places=2),
    PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json"),
]


class ErrorResponse(BaseModel):
    """Structured API error body returned for 400/404/409/422 responses."""

    detail: str = Field(..., description="Human-readable error description.")
    code: str = Field(..., description="Stable machine-readable error code.")
