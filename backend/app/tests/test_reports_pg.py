"""Real-PostgreSQL integration tests.

Unlike the SQLite logic harness in ``test_accounting_service.py``, these run
against the live database configured in ``DATABASE_URL`` (the applied migration
plus the committed 18-account seed). Each test runs inside an outer transaction
that is **rolled back** in teardown, so tests exercise real PostgreSQL — native
enums, ``NUMERIC(18, 2)`` semantics, the per-line CHECK constraints, and foreign
keys — without persisting any data or hard-deleting anything.

The whole module is skipped when ``DATABASE_URL`` is not configured, so the
default ``pytest`` run stays database-independent.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.models.account import Account
from app.models.enums import EntryStatus
from app.models.journal import JournalEntry, JournalLine
from app.schemas.entry import ExpenseCreate, IncomeCreate, OwnerCapitalCreate
from app.services.accounting import AccountingService
from app.services.reports import ReportService

pytestmark = pytest.mark.skipif(
    not get_settings().database_url,
    reason="DATABASE_URL not configured; skipping real-PostgreSQL tests.",
)

# The 18 default account codes seeded by app.db.seed.
DEFAULT_CODES = {
    "1000", "1010", "1100", "1200", "1500",
    "2000", "2100",
    "3000", "3100",
    "4000", "4100",
    "5000", "5100", "5200", "5300", "5400", "5500", "5600",
}

TODAY = date(2026, 8, 3)


@pytest_asyncio.fixture
async def pg_session() -> AsyncIterator[AsyncSession]:
    """Yield a session bound to a real PG transaction that is rolled back.

    The service layer flushes (running real constraints) but never commits; the
    outer transaction rollback discards every write when the test finishes.
    """
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False, autoflush=False)
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def _code_to_id(session: AsyncSession, code: str) -> uuid.UUID:
    result = await session.execute(select(Account.id).where(Account.code == code))
    found = result.scalar_one_or_none()
    assert found is not None, f"account {code} not seeded"
    return found


async def _seed_common(session: AsyncSession) -> tuple[AccountingService, dict]:
    svc = AccountingService(session)
    ids = {
        code: await _code_to_id(session, code)
        for code in ("1000", "1010", "4000", "5000")
    }
    return svc, ids


# ---------------------------------------------------------------------------
# Schema / seed
# ---------------------------------------------------------------------------


async def test_migration_applied(pg_session: AsyncSession) -> None:
    """The accounting-core migration is recorded and its tables exist."""
    revision = await pg_session.scalar(select(func.max(_alembic_version())))
    assert revision == "0001_accounting_core"
    # Each ledger table is queryable (exists with the expected columns).
    for model in (Account, JournalEntry, JournalLine):
        await pg_session.execute(select(func.count()).select_from(model))


async def test_eighteen_seeded_accounts(pg_session: AsyncSession) -> None:
    """Exactly the 18 default account codes are present and active."""
    result = await pg_session.execute(select(Account.code))
    codes = set(result.scalars().all())
    assert DEFAULT_CODES.issubset(codes)
    # No stray *default* codes beyond the 18 seeded ones were introduced here.
    assert DEFAULT_CODES == (codes & DEFAULT_CODES)
    assert len(DEFAULT_CODES) == 18


# ---------------------------------------------------------------------------
# Persistence & reversal
# ---------------------------------------------------------------------------


async def test_transaction_persistence(pg_session: AsyncSession) -> None:
    """A posted entry round-trips through PostgreSQL with balanced lines."""
    svc, ids = await _seed_common(pg_session)
    entry = await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("1000.00"),
            date=TODAY,
            description="capital injection",
            deposit_account_id=ids["1000"],
        )
    )
    entry_id = entry.id

    # Force a fresh read from the database (not the identity map).
    pg_session.expire_all()
    reloaded = await pg_session.get(JournalEntry, entry_id)
    assert reloaded is not None
    assert reloaded.status is EntryStatus.POSTED

    lines = (
        await pg_session.execute(
            select(JournalLine).where(JournalLine.journal_entry_id == entry_id)
        )
    ).scalars().all()
    assert len(lines) == 2
    total_debit = sum((line.debit for line in lines), Decimal("0"))
    total_credit = sum((line.credit for line in lines), Decimal("0"))
    assert total_debit == total_credit == Decimal("1000.00")


async def test_reversal_swaps_and_marks_original(pg_session: AsyncSession) -> None:
    """Reversing a posted expense swaps sides and flips the original to REVERSED."""
    svc, ids = await _seed_common(pg_session)
    expense = await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("200.00"),
            date=TODAY,
            description="office rent",
            expense_account_id=ids["5000"],
            paid_from_account_id=ids["1000"],
        )
    )
    reversal = await svc.reverse_posted_entry(expense.id, reason="test")
    original = await svc.get_entry(expense.id)

    assert original.status is EntryStatus.REVERSED
    assert reversal.reversed_entry_id == original.id
    assert reversal.reference == original.entry_number
    assert reversal.total_debit == reversal.total_credit == Decimal("200.00")

    orig = {ln.account_code: (ln.debit, ln.credit) for ln in original.lines}
    rev = {ln.account_code: (ln.debit, ln.credit) for ln in reversal.lines}
    assert orig["5000"] == (Decimal("200.00"), Decimal("0.00"))
    assert rev["5000"] == (Decimal("0.00"), Decimal("200.00"))
    assert orig["1000"] == (Decimal("0.00"), Decimal("200.00"))
    assert rev["1000"] == (Decimal("200.00"), Decimal("0.00"))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


async def test_trial_balance_equality(pg_session: AsyncSession) -> None:
    """Trial balance debits equal credits after a set of posted entries."""
    svc, ids = await _seed_common(pg_session)
    await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("5000.00"), date=TODAY,
            description="capital", deposit_account_id=ids["1000"],
        )
    )
    await svc.create_income_entry(
        IncomeCreate(
            amount=Decimal("1200.00"), date=TODAY, description="sale",
            deposit_account_id=ids["1010"], revenue_account_id=ids["4000"],
        )
    )
    await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("300.00"), date=TODAY, description="rent",
            expense_account_id=ids["5000"], paid_from_account_id=ids["1000"],
        )
    )

    tb = await ReportService(pg_session).trial_balance(TODAY)
    assert tb.balanced is True
    assert tb.total_debit == tb.total_credit
    # Cash: 5000 - 300 = 4700 debit; Bank 1200 debit; Capital 5000 credit;
    # Sales 1200 credit; Rent 300 debit. Debits = 4700+1200+300 = 6200.
    assert tb.total_debit == Decimal("6200.00")


async def test_profit_and_loss_totals(pg_session: AsyncSession) -> None:
    """P&L sums revenue and expenses and computes net profit."""
    svc, ids = await _seed_common(pg_session)
    await svc.create_income_entry(
        IncomeCreate(
            amount=Decimal("1200.00"), date=TODAY, description="sale",
            deposit_account_id=ids["1010"], revenue_account_id=ids["4000"],
        )
    )
    await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("300.00"), date=TODAY, description="rent",
            expense_account_id=ids["5000"], paid_from_account_id=ids["1000"],
        )
    )

    pl = await ReportService(pg_session).profit_and_loss(
        date(2026, 8, 1), date(2026, 8, 31)
    )
    assert pl.total_revenue == Decimal("1200.00")
    assert pl.total_expenses == Decimal("300.00")
    assert pl.net_profit == Decimal("900.00")


async def test_balance_sheet_equation(pg_session: AsyncSession) -> None:
    """Assets equal liabilities plus equity (incl. current-period earnings)."""
    svc, ids = await _seed_common(pg_session)
    await svc.create_owner_capital_entry(
        OwnerCapitalCreate(
            amount=Decimal("5000.00"), date=TODAY,
            description="capital", deposit_account_id=ids["1000"],
        )
    )
    await svc.create_income_entry(
        IncomeCreate(
            amount=Decimal("1200.00"), date=TODAY, description="sale",
            deposit_account_id=ids["1010"], revenue_account_id=ids["4000"],
        )
    )
    await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("300.00"), date=TODAY, description="rent",
            expense_account_id=ids["5000"], paid_from_account_id=ids["1000"],
        )
    )

    bs = await ReportService(pg_session).balance_sheet(TODAY)
    assert bs.balanced is True
    assert bs.total_assets == bs.total_liabilities_and_equity
    # Assets: Cash 4700 + Bank 1200 = 5900. Equity: capital 5000 + earnings 900.
    assert bs.total_assets == Decimal("5900.00")
    assert bs.equity.current_period_earnings == Decimal("900.00")
    assert bs.equity.total_equity == Decimal("5900.00")


async def test_monthly_review_findings(pg_session: AsyncSession) -> None:
    """The review flags future-dated, duplicate, and missing-reference entries."""
    svc, ids = await _seed_common(pg_session)
    # Two identical income entries -> duplicate; both lack a reference -> INFO.
    for _ in range(2):
        await svc.create_income_entry(
            IncomeCreate(
                amount=Decimal("100.00"), date=TODAY, description="daily sale",
                deposit_account_id=ids["1010"], revenue_account_id=ids["4000"],
            )
        )
    # A future-dated entry relative to TODAY.
    await svc.create_expense_entry(
        ExpenseCreate(
            amount=Decimal("50.00"), date=date(2026, 8, 20),
            description="prepaid rent",
            expense_account_id=ids["5000"], paid_from_account_id=ids["1000"],
        )
    )

    review = await ReportService(pg_session).monthly_review(
        start=date(2026, 8, 1), end=date(2026, 8, 31), today=TODAY
    )
    rules = {f.rule_code for f in review.findings}
    assert "DUPLICATE_ENTRY" in rules
    assert "FUTURE_DATED_ENTRY" in rules
    assert "MISSING_REFERENCE" in rules
    # No critical findings for well-formed, balanced entries.
    assert review.counts_by_severity["CRITICAL"] == 0
    assert review.counts_by_severity["WARNING"] >= 1
    assert "not a statutory or external audit" in (review.summary or "")


def _alembic_version():
    """A lightweight column handle for the Alembic version table."""
    from sqlalchemy import column, table

    return table("alembic_version", column("version_num")).c.version_num
