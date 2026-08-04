"""Report response schemas (deterministic financial reports).

These are the output contracts for the four read-only reports defined in
``specs/05-api-contracts.md``: trial balance, profit & loss, balance sheet, and
the Automated Monthly Accounting Review. All monetary fields are
:class:`~decimal.Decimal` serialized as decimal strings — the same ``MoneyOut``
convention used elsewhere — because these numbers are computed in deterministic
Python (never by the LLM) and must round-trip without binary-float drift.

Signed money note: report balances (e.g. a profit-and-loss amount, a balance
sheet section total, current-period earnings) can legitimately be negative — a
net loss, a contra balance, an overdrawn cash account. They therefore use
``SignedMoneyOut`` (no ``ge=0`` bound), distinct from line-level ``MoneyOut``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

from app.models.enums import AccountType

# Report figures may be negative (net loss, contra balances); serialize as a
# decimal string like MoneyOut but without the non-negative bound.
SignedMoneyOut = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=2),
    PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json"),
]


# ---------------------------------------------------------------------------
# Trial balance
# ---------------------------------------------------------------------------


class TrialBalanceRow(BaseModel):
    """One account's net balance placed on its normal side."""

    account_code: str
    account_name: str
    account_type: AccountType
    debit_balance: SignedMoneyOut
    credit_balance: SignedMoneyOut


class TrialBalanceOut(BaseModel):
    """Trial balance as of a date. ``balanced`` is total_debit == total_credit."""

    as_of: date
    rows: list[TrialBalanceRow]
    total_debit: SignedMoneyOut
    total_credit: SignedMoneyOut
    balanced: bool


# ---------------------------------------------------------------------------
# Profit & loss
# ---------------------------------------------------------------------------


class AmountRow(BaseModel):
    """An account and its amount for a period (revenue or expense line)."""

    account_code: str
    account_name: str
    amount: SignedMoneyOut


class ProfitLossOut(BaseModel):
    """Revenue and expenses over ``[start, end]`` with the net result."""

    start: date
    end: date
    revenue: list[AmountRow]
    expenses: list[AmountRow]
    total_revenue: SignedMoneyOut
    total_expenses: SignedMoneyOut
    net_profit: SignedMoneyOut


# ---------------------------------------------------------------------------
# Balance sheet
# ---------------------------------------------------------------------------


class BalanceRow(BaseModel):
    """An account and its balance for a balance-sheet section."""

    account_code: str
    account_name: str
    amount: SignedMoneyOut


class EquitySection(BaseModel):
    """Equity broken into capital, drawings, and current-period earnings."""

    owner_capital: SignedMoneyOut
    owner_drawings: SignedMoneyOut
    current_period_earnings: SignedMoneyOut
    total_equity: SignedMoneyOut


class BalanceSheetOut(BaseModel):
    """Assets, liabilities, and equity as of a date. ``balanced`` = A == L+E."""

    as_of: date
    assets: list[BalanceRow]
    liabilities: list[BalanceRow]
    equity: EquitySection
    total_assets: SignedMoneyOut
    total_liabilities_and_equity: SignedMoneyOut
    balanced: bool


# ---------------------------------------------------------------------------
# Automated Monthly Accounting Review
# ---------------------------------------------------------------------------


class ReviewFinding(BaseModel):
    """A single review observation.

    This is an internal consistency/quality check — NOT a statutory or external
    audit and NOT a formal audit opinion.
    """

    rule_code: str
    severity: str  # INFO | WARNING | CRITICAL
    message: str
    entry_id: str | None = None
    entry_number: str | None = None
    details: dict | None = None


class MonthlyReviewOut(BaseModel):
    """Automated Monthly Accounting Review over ``[period_start, period_end]``."""

    period_start: date
    period_end: date
    findings: list[ReviewFinding]
    counts_by_severity: dict[str, int]
    summary: str | None = None
