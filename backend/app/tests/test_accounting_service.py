"""Service-logic tests for the double-entry accounting core.

Run against an in-memory SQLite harness (see ``__init__.py`` for the PostgreSQL
coverage caveat). They verify the accounting *logic*: template construction,
balance enforcement, account validation, entry numbering, posting, reversal,
draft update, search, listing, and seed idempotency.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.seed import DEFAULT_ACCOUNTS, seed_accounts
from app.models.account import Account
from app.models.enums import EntrySource, EntryStatus
from app.models.journal import JournalEntry
from app.schemas.account import AccountCreate
from app.schemas.entry import (
    EntryUpdate,
    ExpenseCreate,
    IncomeCreate,
    LineInput,
    OwnerCapitalCreate,
    OwnerWithdrawalCreate,
    TransferCreate,
    VendorBillCreate,
    VendorPaymentCreate,
)
from app.services.accounting import AccountingService
from app.tests.conftest import account_id

_DATE = date(2026, 1, 15)


async def _acct(session: AsyncSession, code: str) -> uuid.UUID:
    return await account_id(session, code)


# --- 1-7: the seven templates each produce a balanced POSTED entry ---------


async def test_owner_capital_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("50000.00"),
            date=_DATE,
            description="Initial capital",
            deposit_account_id=await _acct(seeded_session, "1000"),
        )
    )
    assert entry.status is EntryStatus.POSTED
    assert entry.source is EntrySource.MANUAL
    assert len(entry.lines) == 2
    assert entry.total_debit == entry.total_credit == Decimal("50000.00")
    # Dr Cash, Cr Owner Capital
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["1000"].debit == Decimal("50000.00")
    assert by_code["3000"].credit == Decimal("50000.00")


async def test_income_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.create_income_entry(
        IncomeCreate(
            amount=Decimal("1200.00"),
            date=_DATE,
            description="Consulting",
            deposit_account_id=await _acct(seeded_session, "1010"),
            revenue_account_id=await _acct(seeded_session, "4100"),
        )
    )
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["1010"].debit == Decimal("1200.00")
    assert by_code["4100"].credit == Decimal("1200.00")
    assert entry.total_debit == entry.total_credit


async def test_expense_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("300.00"),
            date=_DATE,
            description="Rent",
            expense_account_id=await _acct(seeded_session, "5000"),
            paid_from_account_id=await _acct(seeded_session, "1000"),
        )
    )
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["5000"].debit == Decimal("300.00")
    assert by_code["1000"].credit == Decimal("300.00")


async def test_vendor_bill_credits_accounts_payable(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.create_vendor_bill(
        VendorBillCreate(
            amount=Decimal("450.00"),
            date=_DATE,
            description="Supplies on credit",
            expense_or_asset_account_id=await _acct(seeded_session, "5200"),
        )
    )
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["5200"].debit == Decimal("450.00")
    assert by_code["2000"].credit == Decimal("450.00")


async def test_vendor_payment_debits_accounts_payable(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.record_vendor_payment(
        VendorPaymentCreate(
            amount=Decimal("450.00"),
            date=_DATE,
            description="Pay supplier",
            paid_from_account_id=await _acct(seeded_session, "1010"),
        )
    )
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["2000"].debit == Decimal("450.00")
    assert by_code["1010"].credit == Decimal("450.00")


async def test_owner_withdrawal_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.create_owner_withdrawal(
        OwnerWithdrawalCreate(
            amount=Decimal("200.00"),
            date=_DATE,
            description="Owner draw",
            paid_from_account_id=await _acct(seeded_session, "1000"),
        )
    )
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["3100"].debit == Decimal("200.00")
    assert by_code["1000"].credit == Decimal("200.00")


async def test_transfer_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    entry = await svc.transfer_funds(
        TransferCreate(
            amount=Decimal("1000.00"),
            date=_DATE,
            description="Cash to bank",
            from_account_id=await _acct(seeded_session, "1000"),
            to_account_id=await _acct(seeded_session, "1010"),
        )
    )
    by_code = {line.account.code: line for line in entry.lines}
    assert by_code["1010"].debit == Decimal("1000.00")  # destination debited
    assert by_code["1000"].credit == Decimal("1000.00")  # source credited


# --- 8-12: validation failures ---------------------------------------------


async def test_transfer_same_account_rejected(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    cash = await _acct(seeded_session, "1000")
    # Bypass the Pydantic guard to prove the service also rejects it.
    payload = TransferCreate.model_construct(
        amount=Decimal("100.00"),
        date=_DATE,
        description="x",
        memo=None,
        from_account_id=cash,
        to_account_id=cash,
    )
    with pytest.raises(ValidationError):
        await svc.transfer_funds(payload)


async def test_nonexistent_account_raises_not_found(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    with pytest.raises(NotFoundError):
        await svc.create_owner_capital_entry(
            OwnerCapitalCreate(
                amount=Decimal("10.00"),
                date=_DATE,
                description="x",
                deposit_account_id=uuid.uuid4(),
            )
        )


async def test_inactive_account_rejected(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    cash = await seeded_session.get(Account, await _acct(seeded_session, "1000"))
    assert cash is not None
    cash.is_active = False
    await seeded_session.flush()
    with pytest.raises(ValidationError):
        await svc.create_owner_capital_entry(
            OwnerCapitalCreate(
                amount=Decimal("10.00"),
                date=_DATE,
                description="x",
                deposit_account_id=cash.id,
            )
        )


async def test_expense_template_rejects_revenue_account(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    with pytest.raises(ValidationError):
        await svc.create_expense_entry(
            ExpenseCreate(
                amount=Decimal("10.00"),
                date=_DATE,
                description="x",
                expense_account_id=await _acct(seeded_session, "4000"),  # REVENUE
                paid_from_account_id=await _acct(seeded_session, "1000"),
            )
        )


async def test_income_template_rejects_non_asset_deposit(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    with pytest.raises(ValidationError):
        await svc.create_income_entry(
            IncomeCreate(
                amount=Decimal("10.00"),
                date=_DATE,
                description="x",
                deposit_account_id=await _acct(seeded_session, "4000"),  # not ASSET
                revenue_account_id=await _acct(seeded_session, "4100"),
            )
        )


# --- 13-14: entry numbering -------------------------------------------------


async def test_entry_numbers_are_sequential_and_formatted(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    first = await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("1.00"), date=_DATE, description="a",
            deposit_account_id=await _acct(seeded_session, "1000"),
        )
    )
    second = await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("2.00"), date=_DATE, description="b",
            deposit_account_id=await _acct(seeded_session, "1000"),
        )
    )
    assert first.entry_number == "JE-2026-000001"
    assert second.entry_number == "JE-2026-000002"


# --- 15-16: posting ---------------------------------------------------------


async def _make_draft(session: AsyncSession) -> JournalEntry:
    """Insert a balanced DRAFT entry directly for post/update tests."""
    from app.models.journal import JournalLine

    cash = await account_id(session, "1000")
    capital = await account_id(session, "3000")
    entry = JournalEntry(
        entry_number="JE-2026-000900",
        entry_date=_DATE,
        description="draft",
        source=EntrySource.MANUAL,
        status=EntryStatus.DRAFT,
        lines=[
            JournalLine(account_id=cash, debit=Decimal("10.00"), credit=Decimal("0")),
            JournalLine(account_id=capital, debit=Decimal("0"), credit=Decimal("10.00")),
        ],
    )
    session.add(entry)
    await session.flush()
    return entry


async def test_post_draft_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    draft = await _make_draft(seeded_session)
    posted = await svc.post_entry(draft.id)
    assert posted.status is EntryStatus.POSTED


async def test_post_already_posted_rejected(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    draft = await _make_draft(seeded_session)
    await svc.post_entry(draft.id)
    with pytest.raises(ConflictError):
        await svc.post_entry(draft.id)


# --- 17-21: reversal --------------------------------------------------------


async def test_reversal_swaps_sides_and_links(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    original = await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("500.00"), date=_DATE, description="cap",
            deposit_account_id=await _acct(seeded_session, "1000"),
        )
    )
    reversal = await svc.reverse_posted_entry(original.id, reason="mistake")

    assert reversal.reversed_entry_id == original.id
    assert reversal.reference == original.entry_number
    assert reversal.source is EntrySource.SYSTEM
    # sides swapped
    orig_by_code = {line.account.code: line for line in original.lines}
    rev_by_code = {line.account.code: line for line in reversal.lines}
    assert rev_by_code["1000"].credit == orig_by_code["1000"].debit
    assert rev_by_code["3000"].debit == orig_by_code["3000"].credit
    # original now REVERSED
    refreshed = await svc.get_entry(original.id)
    assert refreshed.status is EntryStatus.REVERSED


async def test_double_reversal_blocked(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    original = await svc.create_income_entry(
        IncomeCreate(
            amount=Decimal("100.00"), date=_DATE, description="inc",
            deposit_account_id=await _acct(seeded_session, "1000"),
            revenue_account_id=await _acct(seeded_session, "4000"),
        )
    )
    await svc.reverse_posted_entry(original.id)
    with pytest.raises(ConflictError):
        await svc.reverse_posted_entry(original.id)


async def test_reverse_draft_blocked(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    draft = await _make_draft(seeded_session)
    with pytest.raises(ConflictError):
        await svc.reverse_posted_entry(draft.id)


# --- 22-23: draft update ----------------------------------------------------


async def test_update_draft_entry(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    draft = await _make_draft(seeded_session)
    cash = await _acct(seeded_session, "1000")
    capital = await _acct(seeded_session, "3000")
    updated = await svc.update_draft_entry(
        draft.id,
        EntryUpdate(
            description="edited",
            lines=[
                LineInput(account_id=cash, debit=Decimal("25.00")),
                LineInput(account_id=capital, credit=Decimal("25.00")),
            ],
        ),
    )
    assert updated.description == "edited"
    assert updated.total_debit == Decimal("25.00")


async def test_update_posted_entry_blocked(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    posted = await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("10.00"), date=_DATE, description="cap",
            deposit_account_id=await _acct(seeded_session, "1000"),
        )
    )
    with pytest.raises(ConflictError):
        await svc.update_draft_entry(posted.id, EntryUpdate(description="nope"))


async def test_update_draft_unbalanced_rejected(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    draft = await _make_draft(seeded_session)
    cash = await _acct(seeded_session, "1000")
    capital = await _acct(seeded_session, "3000")
    with pytest.raises(ValidationError):
        await svc.update_draft_entry(
            draft.id,
            EntryUpdate(
                lines=[
                    LineInput(account_id=cash, debit=Decimal("25.00")),
                    LineInput(account_id=capital, credit=Decimal("30.00")),
                ],
            ),
        )


# --- 24: reads --------------------------------------------------------------


async def test_get_missing_entry_raises_not_found(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    with pytest.raises(NotFoundError):
        await svc.get_entry(uuid.uuid4())


# --- 25: search -------------------------------------------------------------


async def test_search_filters_by_status_and_text(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("1.00"), date=_DATE, description="Seed capital injection",
            deposit_account_id=await _acct(seeded_session, "1000"),
        )
    )
    await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("2.00"), date=_DATE, description="Coffee run",
            expense_account_id=await _acct(seeded_session, "5600"),
            paid_from_account_id=await _acct(seeded_session, "1000"),
        )
    )
    items, total = await svc.search_entries(status=EntryStatus.POSTED)
    assert total == 2
    items, total = await svc.search_entries(query="capital")
    assert total == 1
    assert "capital" in items[0].description.lower()


async def test_search_filters_by_account(seeded_session: AsyncSession) -> None:
    svc = AccountingService(seeded_session)
    await svc.create_income_entry(
        IncomeCreate(
            amount=Decimal("5.00"), date=_DATE, description="svc",
            deposit_account_id=await _acct(seeded_session, "1010"),
            revenue_account_id=await _acct(seeded_session, "4100"),
        )
    )
    _, total_bank = await svc.search_entries(account_id=await _acct(seeded_session, "1010"))
    _, total_cash = await svc.search_entries(account_id=await _acct(seeded_session, "1000"))
    assert total_bank == 1
    assert total_cash == 0


# --- 26: accounts -----------------------------------------------------------


async def test_list_accounts_and_filter_by_type(seeded_session: AsyncSession) -> None:
    from app.models.enums import AccountType

    svc = AccountingService(seeded_session)
    all_accounts = await svc.list_accounts()
    assert len(all_accounts) == 18
    assets = await svc.list_accounts(type_=AccountType.ASSET)
    assert len(assets) == 5
    assert all(a.type is AccountType.ASSET for a in assets)


async def test_create_account_and_reject_duplicate_code(seeded_session: AsyncSession) -> None:
    from app.models.enums import AccountType

    svc = AccountingService(seeded_session)
    created = await svc.create_account(
        AccountCreate(code="5700", name="Software", type=AccountType.EXPENSE)
    )
    assert created.code == "5700"
    with pytest.raises(ConflictError):
        await svc.create_account(
            AccountCreate(code="5700", name="Dup", type=AccountType.EXPENSE)
        )


# --- 27: seed idempotency ---------------------------------------------------


async def test_seed_is_idempotent(session: AsyncSession) -> None:
    inserted_first = await seed_accounts(session)
    await session.commit()
    inserted_second = await seed_accounts(session)
    await session.commit()
    assert inserted_first == len(DEFAULT_ACCOUNTS) == 18
    assert inserted_second == 0
    total = await session.scalar(select(JournalEntry.id).limit(1))
    assert total is None  # seeding accounts creates no entries
    count = len((await session.execute(select(Account))).scalars().all())
    assert count == 18
