"""Account request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AccountType


class AccountCreate(BaseModel):
    """Request body for creating an account."""

    code: str = Field(..., min_length=1, max_length=10, description='e.g. "5100"')
    name: str = Field(..., min_length=1, description='e.g. "Utilities"')
    type: AccountType


class AccountOut(BaseModel):
    """Account as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    type: AccountType
    is_active: bool
    created_at: datetime
