"""Database-independent validation tests for the accounting Pydantic schemas.

These exercise the edge-layer rules (positive money, decimal-string output,
line one-sided-ness, distinct transfer accounts) with no database involved.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.schemas.common import ErrorResponse
from app.schemas.entry import (
    EntryUpdate,
    LineInput,
    OwnerCapitalCreate,
    TransferCreate,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def test_positive_money_accepts_valid_amount() -> None:
    model = OwnerCapitalCreate(
        amount=Decimal("50000.00"),
        date="2026-01-15",
        description="Initial capital",
        deposit_account_id=_uuid(),
    )
    assert model.amount == Decimal("50000.00")


@pytest.mark.parametrize("bad", ["0", "-1", "-0.01"])
def test_positive_money_rejects_zero_or_negative(bad: str) -> None:
    with pytest.raises(PydanticValidationError):
        OwnerCapitalCreate(
            amount=Decimal(bad),
            date="2026-01-15",
            description="x",
            deposit_account_id=_uuid(),
        )


def test_amount_rejects_more_than_two_decimal_places() -> None:
    with pytest.raises(PydanticValidationError):
        OwnerCapitalCreate(
            amount=Decimal("10.001"),
            date="2026-01-15",
            description="x",
            deposit_account_id=_uuid(),
        )


def test_missing_date_is_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        OwnerCapitalCreate(
            amount=Decimal("10.00"),
            description="x",
            deposit_account_id=_uuid(),
        )


def test_blank_description_is_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        OwnerCapitalCreate(
            amount=Decimal("10.00"),
            date="2026-01-15",
            description="",
            deposit_account_id=_uuid(),
        )


def test_transfer_rejects_same_source_and_destination() -> None:
    same = _uuid()
    with pytest.raises(PydanticValidationError):
        TransferCreate(
            amount=Decimal("100.00"),
            date="2026-01-15",
            description="move",
            from_account_id=same,
            to_account_id=same,
        )


def test_transfer_allows_distinct_accounts() -> None:
    model = TransferCreate(
        amount=Decimal("100.00"),
        date="2026-01-15",
        description="move",
        from_account_id=_uuid(),
        to_account_id=_uuid(),
    )
    assert model.from_account_id != model.to_account_id


def test_line_requires_exactly_one_side() -> None:
    # both sides -> invalid
    with pytest.raises(PydanticValidationError):
        LineInput(account_id=_uuid(), debit=Decimal("1.00"), credit=Decimal("1.00"))
    # neither side -> invalid
    with pytest.raises(PydanticValidationError):
        LineInput(account_id=_uuid())
    # exactly one -> valid
    ok = LineInput(account_id=_uuid(), debit=Decimal("1.00"))
    assert ok.debit == Decimal("1.00")
    assert ok.credit is None


def test_entry_update_requires_at_least_two_lines() -> None:
    with pytest.raises(PydanticValidationError):
        EntryUpdate(lines=[LineInput(account_id=_uuid(), debit=Decimal("1.00"))])


def test_money_out_serializes_as_decimal_string() -> None:
    from app.schemas.entry import LineOut

    line = LineOut(
        id=_uuid(),
        account_id=_uuid(),
        account_code="1000",
        account_name="Cash",
        debit=Decimal("100"),
        credit=Decimal("0"),
    )
    dumped = line.model_dump(mode="json")
    assert dumped["debit"] == "100.00"
    assert dumped["credit"] == "0.00"


def test_error_response_shape() -> None:
    err = ErrorResponse(detail="boom", code="conflict")
    assert err.model_dump() == {"detail": "boom", "code": "conflict"}
