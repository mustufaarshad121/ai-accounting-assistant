"""Default chart-of-accounts seed.

Seeds the 18 accounts defined in ``specs/04-accounting-rules.md``. The seed is
**idempotent**: it inserts only codes that are not already present, so running
it repeatedly (on every deploy, in tests, or by hand) never creates duplicates
and never mutates existing accounts. Codes are the stable identity; names/types
here are the canonical defaults for a fresh ledger.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import AccountType

# (code, name, type) — the canonical default chart. Order is display order.
DEFAULT_ACCOUNTS: tuple[tuple[str, str, AccountType], ...] = (
    ("1000", "Cash", AccountType.ASSET),
    ("1010", "Bank", AccountType.ASSET),
    ("1100", "Accounts Receivable", AccountType.ASSET),
    ("1200", "Prepaid Expenses", AccountType.ASSET),
    ("1500", "Equipment", AccountType.ASSET),
    ("2000", "Accounts Payable", AccountType.LIABILITY),
    ("2100", "Loan Payable", AccountType.LIABILITY),
    ("3000", "Owner Capital", AccountType.EQUITY),
    ("3100", "Owner Drawings", AccountType.EQUITY),
    ("4000", "Sales Revenue", AccountType.REVENUE),
    ("4100", "Service Revenue", AccountType.REVENUE),
    ("5000", "Office Rent", AccountType.EXPENSE),
    ("5100", "Utilities", AccountType.EXPENSE),
    ("5200", "Office Supplies", AccountType.EXPENSE),
    ("5300", "Salaries", AccountType.EXPENSE),
    ("5400", "Marketing Expense", AccountType.EXPENSE),
    ("5500", "Travel Expense", AccountType.EXPENSE),
    ("5600", "Miscellaneous Expense", AccountType.EXPENSE),
)


async def seed_accounts(session: AsyncSession) -> int:
    """Insert any missing default accounts. Returns the number inserted.

    Idempotent: existing codes are left untouched. The caller owns the
    transaction (commit/rollback); this function only adds and flushes.
    """
    result = await session.execute(select(Account.code))
    existing = set(result.scalars().all())

    inserted = 0
    for code, name, type_ in DEFAULT_ACCOUNTS:
        if code in existing:
            continue
        session.add(Account(code=code, name=name, type=type_))
        inserted += 1

    if inserted:
        await session.flush()
    return inserted


async def _run() -> None:
    """Apply the seed against the configured database, then commit.

    Requires ``DATABASE_URL`` to be set. Safe to run repeatedly (idempotent).
    Intended to be invoked once after the accounting-core migration is applied:
    ``uv run python -m app.db.seed``.
    """
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        inserted = await seed_accounts(session)
        await session.commit()
    print(f"Seed complete: {inserted} account(s) inserted.")


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    import asyncio

    asyncio.run(_run())
