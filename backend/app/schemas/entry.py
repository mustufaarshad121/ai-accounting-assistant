"""Journal entry request/response schemas.

Covers the seven transaction templates, the generic draft update, the reversal
request, and the read models (line + entry + paginated list). Every monetary
field is a positive ``Decimal`` on input; output money is serialized as a
decimal string. Validation here is the edge layer (Pydantic); cross-account
and balance rules live in the service layer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EntrySource, EntryStatus
from app.schemas.common import MoneyOut, PositiveMoney

# ---------------------------------------------------------------------------
# Transaction template requests (one per accounting flow in specs/04)
# ---------------------------------------------------------------------------


class _TemplateBase(BaseModel):
    """Common fields shared by every template request."""

    amount: PositiveMoney
    date: date
    description: str = Field(..., min_length=1)
    memo: str | None = None


class OwnerCapitalCreate(_TemplateBase):
    """Owner investment: Dr Cash/Bank · Cr Owner Capital."""

    deposit_account_id: uuid.UUID


class IncomeCreate(_TemplateBase):
    """Cash income: Dr Cash/Bank · Cr Revenue."""

    deposit_account_id: uuid.UUID
    revenue_account_id: uuid.UUID


class ExpenseCreate(_TemplateBase):
    """Paid expense: Dr Expense · Cr Cash/Bank."""

    expense_account_id: uuid.UUID
    paid_from_account_id: uuid.UUID


class VendorBillCreate(_TemplateBase):
    """Vendor bill: Dr Expense/Asset · Cr Accounts Payable."""

    expense_or_asset_account_id: uuid.UUID


class VendorPaymentCreate(_TemplateBase):
    """Vendor payment: Dr Accounts Payable · Cr Cash/Bank."""

    paid_from_account_id: uuid.UUID


class OwnerWithdrawalCreate(_TemplateBase):
    """Owner withdrawal: Dr Owner Drawings · Cr Cash/Bank."""

    paid_from_account_id: uuid.UUID


class TransferCreate(_TemplateBase):
    """Fund transfer: Dr destination Cash/Bank · Cr source Cash/Bank."""

    from_account_id: uuid.UUID
    to_account_id: uuid.UUID

    @model_validator(mode="after")
    def _distinct_accounts(self) -> TransferCreate:
        if self.from_account_id == self.to_account_id:
            raise ValueError("from_account_id and to_account_id must differ")
        return self


# ---------------------------------------------------------------------------
# Update / reverse requests
# ---------------------------------------------------------------------------


class LineInput(BaseModel):
    """A single line supplied when editing a draft entry."""

    account_id: uuid.UUID
    debit: PositiveMoney | None = None
    credit: PositiveMoney | None = None
    memo: str | None = None

    @model_validator(mode="after")
    def _exactly_one_side(self) -> LineInput:
        has_debit = self.debit is not None
        has_credit = self.credit is not None
        if has_debit == has_credit:
            raise ValueError("exactly one of debit or credit must be provided")
        return self


class EntryUpdate(BaseModel):
    """Patch a DRAFT entry. Any subset of fields may be provided."""

    description: str | None = Field(default=None, min_length=1)
    entry_date: date | None = None
    reference: str | None = None
    lines: list[LineInput] | None = Field(default=None, min_length=2)


class ReverseRequest(BaseModel):
    """Reverse a POSTED entry."""

    reason: str | None = None


# ---------------------------------------------------------------------------
# Read models
# ---------------------------------------------------------------------------


class LineOut(BaseModel):
    """A journal line enriched with its account code/name for display."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    account_code: str
    account_name: str
    debit: MoneyOut
    credit: MoneyOut
    memo: str | None = None


class EntryOut(BaseModel):
    """A journal entry with its lines and computed totals."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_number: str
    entry_date: date
    description: str
    source: EntrySource
    status: EntryStatus
    reference: str | None = None
    reversed_entry_id: uuid.UUID | None = None
    lines: list[LineOut]
    total_debit: MoneyOut
    total_credit: MoneyOut
    created_at: datetime
    updated_at: datetime


class EntryListOut(BaseModel):
    """Paginated list of entries."""

    items: list[EntryOut]
    total: int
