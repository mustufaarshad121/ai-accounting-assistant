"""Journal entry endpoints.

Read/list, the seven transaction templates, draft update, explicit post, and
reversal. Handlers are thin: they validate input via Pydantic, delegate to
:class:`AccountingService` for all accounting logic, commit the unit of work
once on success, and serialize the result. Structured errors (400/404/409/422)
are raised by the service and rendered by the app-wide ``AppError`` handler.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_accounting_service
from app.db.session import get_session
from app.models.enums import EntrySource, EntryStatus
from app.schemas.entry import (
    EntryListOut,
    EntryOut,
    EntryUpdate,
    ExpenseCreate,
    IncomeCreate,
    OwnerCapitalCreate,
    OwnerWithdrawalCreate,
    ReverseRequest,
    TransferCreate,
    VendorBillCreate,
    VendorPaymentCreate,
)
from app.services.accounting import AccountingService

router = APIRouter(prefix="/entries", tags=["entries"])


# -- read / list ------------------------------------------------------------


@router.get("", response_model=EntryListOut)
async def list_entries(
    start: date | None = Query(default=None, description="Earliest entry date (inclusive)."),
    end: date | None = Query(default=None, description="Latest entry date (inclusive)."),
    account_id: uuid.UUID | None = Query(
        default=None, description="Only entries touching this account."
    ),
    source: EntrySource | None = Query(default=None),
    status_: EntryStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, description="Search description/reference/number."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: AccountingService = Depends(get_accounting_service),
) -> EntryListOut:
    """List/search entries with date, account, source, status, and text filters."""
    items, total = await service.search_entries(
        start=start,
        end=end,
        account_id=account_id,
        source=source,
        status=status_,
        query=q,
        limit=limit,
        offset=offset,
    )
    return EntryListOut(items=[EntryOut.model_validate(e) for e in items], total=total)


@router.get("/{entry_id}", response_model=EntryOut)
async def get_entry(
    entry_id: uuid.UUID,
    service: AccountingService = Depends(get_accounting_service),
) -> EntryOut:
    """Return a single entry (404 if missing)."""
    entry = await service.get_entry(entry_id)
    return EntryOut.model_validate(entry)


# -- create (one route per template) ----------------------------------------


@router.post("/owner-capital", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_owner_capital(
    body: OwnerCapitalCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Owner investment: Dr Cash/Bank · Cr Owner Capital."""
    entry = await service.create_owner_capital_entry(body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/income", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_income(
    body: IncomeCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Cash income: Dr Cash/Bank · Cr Revenue."""
    entry = await service.create_income_entry(body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/expense", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: ExpenseCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Paid expense: Dr Expense · Cr Cash/Bank."""
    entry = await service.create_expense_entry(body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/vendor-bill", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_vendor_bill(
    body: VendorBillCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Vendor bill: Dr Expense/Asset · Cr Accounts Payable."""
    entry = await service.create_vendor_bill(body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/vendor-payment", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_vendor_payment(
    body: VendorPaymentCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Vendor payment: Dr Accounts Payable · Cr Cash/Bank."""
    entry = await service.record_vendor_payment(body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/owner-withdrawal", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_owner_withdrawal(
    body: OwnerWithdrawalCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Owner withdrawal: Dr Owner Drawings · Cr Cash/Bank."""
    entry = await service.create_owner_withdrawal(body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/transfer", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: TransferCreate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Fund transfer: Dr destination Cash/Bank · Cr source Cash/Bank."""
    entry = await service.transfer_funds(body)
    await session.commit()
    return EntryOut.model_validate(entry)


# -- update / post / reverse ------------------------------------------------


@router.patch("/{entry_id}", response_model=EntryOut)
async def update_entry(
    entry_id: uuid.UUID,
    body: EntryUpdate,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Edit a DRAFT entry. POSTED/REVERSED → 409 (use reverse)."""
    entry = await service.update_draft_entry(entry_id, body)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/{entry_id}/post", response_model=EntryOut)
async def post_entry(
    entry_id: uuid.UUID,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Transition a DRAFT entry to POSTED (re-checks balance)."""
    entry = await service.post_entry(entry_id)
    await session.commit()
    return EntryOut.model_validate(entry)


@router.post("/{entry_id}/reverse", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
async def reverse_entry(
    entry_id: uuid.UUID,
    body: ReverseRequest,
    service: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_session),
) -> EntryOut:
    """Reverse a POSTED entry; returns the new reversal entry. DRAFT/REVERSED → 409."""
    entry = await service.reverse_posted_entry(entry_id, reason=body.reason)
    await session.commit()
    return EntryOut.model_validate(entry)
