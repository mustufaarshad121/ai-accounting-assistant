"""Report endpoints (read-only, deterministic).

Thin handlers: parse query params, delegate to :class:`ReportService`, and
serialize. All figures are computed in deterministic Decimal Python from
PostgreSQL data — no accounting math and no LLM in this layer. These routes are
read-only and never commit.

The ``as_of`` / ``start`` / ``end`` parameters default to sensible current
values when omitted so the endpoints are usable without a date picker; callers
may always pass explicit dates.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_report_service
from app.core.clock import today as clock_today
from app.schemas.report import (
    BalanceSheetOut,
    MonthlyReviewOut,
    ProfitLossOut,
    TrialBalanceOut,
)
from app.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def _month_start(d: date) -> date:
    """First day of ``d``'s month."""
    return d.replace(day=1)


@router.get("/trial-balance", response_model=TrialBalanceOut)
async def trial_balance(
    as_of: date | None = Query(
        default=None, description="Balance date (defaults to today)."
    ),
    service: ReportService = Depends(get_report_service),
) -> TrialBalanceOut:
    """Trial balance as of a date; total debits must equal total credits."""
    return await service.trial_balance(as_of or clock_today())


@router.get("/profit-loss", response_model=ProfitLossOut)
async def profit_loss(
    start: date | None = Query(
        default=None, description="Period start (defaults to first of this month)."
    ),
    end: date | None = Query(
        default=None, description="Period end (defaults to today)."
    ),
    service: ReportService = Depends(get_report_service),
) -> ProfitLossOut:
    """Profit & loss over ``[start, end]``."""
    today = clock_today()
    return await service.profit_and_loss(start or _month_start(today), end or today)


@router.get("/balance-sheet", response_model=BalanceSheetOut)
async def balance_sheet(
    as_of: date | None = Query(
        default=None, description="Balance date (defaults to today)."
    ),
    service: ReportService = Depends(get_report_service),
) -> BalanceSheetOut:
    """Balance sheet as of a date; assets must equal liabilities + equity."""
    return await service.balance_sheet(as_of or clock_today())


@router.get("/monthly-review", response_model=MonthlyReviewOut)
async def monthly_review(
    start: date | None = Query(
        default=None, description="Period start (defaults to first of this month)."
    ),
    end: date | None = Query(
        default=None, description="Period end (defaults to today)."
    ),
    service: ReportService = Depends(get_report_service),
) -> MonthlyReviewOut:
    """Automated Monthly Accounting Review (internal checks, not an audit)."""
    today = clock_today()
    return await service.monthly_review(
        start=start or _month_start(today),
        end=end or today,
        today=today,
    )
