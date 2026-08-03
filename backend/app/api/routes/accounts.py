"""Account endpoints (chart of accounts).

Thin handlers: validate via Pydantic, delegate to :class:`AccountingService`,
commit the unit of work, and serialize. No accounting logic here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_accounting_service
from app.db.session import get_session
from app.models.enums import AccountType
from app.schemas.account import AccountCreate, AccountOut
from app.services.accounting import AccountingService

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    type: AccountType | None = Query(default=None, description="Filter by account type."),
    is_active: bool | None = Query(default=None, description="Filter by active flag."),
    service: AccountingService = Depends(get_accounting_service),
) -> list[AccountOut]:
    """List accounts, optionally filtered by type and active flag."""
    accounts = await service.list_accounts(type_=type, is_active=is_active)
    return [AccountOut.model_validate(a) for a in accounts]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    """Create a new account (unique code enforced)."""
    account = await service.create_account(body)
    await session.commit()
    return AccountOut.model_validate(account)
