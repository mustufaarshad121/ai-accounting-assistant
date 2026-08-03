"""Double-entry accounting service.

All accounting business logic lives here; API routes and (later) agent tools
stay thin and delegate to this service. The service owns the hard invariants:

* every posted/created entry balances — ``sum(debits) == sum(credits)`` — with
  at least two lines, enforced transactionally before any row is written;
* money is always :class:`~decimal.Decimal`, quantized to two places;
* referenced accounts must exist, be active, and match the template's expected
  account type (e.g. an expense template cannot point at a REVENUE account);
* posted entries are immutable and are corrected only via reversal, which
  swaps debit/credit sides and links back to the original.

Transaction boundary: service methods ``flush`` (assigning ids and running DB
constraints) but do **not** ``commit``. The caller — the FastAPI route via its
session dependency, or a test — owns the commit/rollback, so a failure anywhere
in a request rolls back the whole unit of work with no partial writes.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.account import Account
from app.models.enums import AccountType, EntrySource, EntryStatus
from app.models.journal import JournalEntry, JournalLine
from app.schemas.account import AccountCreate
from app.schemas.entry import (
    EntryUpdate,
    ExpenseCreate,
    IncomeCreate,
    OwnerCapitalCreate,
    OwnerWithdrawalCreate,
    TransferCreate,
    VendorBillCreate,
    VendorPaymentCreate,
)

# Fixed accounts the templates always target, addressed by their seed code so
# callers never have to know the underlying ids.
CODE_OWNER_CAPITAL = "3000"
CODE_OWNER_DRAWINGS = "3100"
CODE_ACCOUNTS_PAYABLE = "2000"

MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class _LineSpec:
    """An intermediate, validated line before it becomes a ``JournalLine``."""

    account: Account
    debit: Decimal
    credit: Decimal
    memo: str | None = None


def _money(value: Decimal) -> Decimal:
    """Quantize an amount to two decimal places (never float)."""
    return value.quantize(MONEY_QUANTUM)


class AccountingService:
    """Coordinates account and journal-entry operations for one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- account lookups -----------------------------------------------------

    async def _get_account(
        self,
        account_id: uuid.UUID,
        *,
        allowed_types: Sequence[AccountType] | None = None,
        require_active: bool = True,
    ) -> Account:
        """Fetch and validate an account referenced by a request.

        Raises:
            NotFoundError: the account id does not exist.
            ValidationError: the account is inactive, or its type is not among
                ``allowed_types`` for this template.
        """
        account = await self._session.get(Account, account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} does not exist.")
        if require_active and not account.is_active:
            raise ValidationError(f"Account {account.code} is inactive.")
        if allowed_types is not None and account.type not in allowed_types:
            allowed = ", ".join(t.value for t in allowed_types)
            raise ValidationError(
                f"Account {account.code} is {account.type.value}; "
                f"this template requires one of: {allowed}."
            )
        return account

    async def _get_account_by_code(self, code: str) -> Account:
        """Fetch a fixed template account by its seed code."""
        result = await self._session.execute(
            select(Account).where(Account.code == code)
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise NotFoundError(
                f"Required account {code} is missing; seed the chart of accounts."
            )
        return account

    # -- entry number --------------------------------------------------------

    async def _next_entry_number(self, entry_date: date) -> str:
        """Allocate the next ``JE-{YYYY}-{seq}`` number for the entry's year.

        Runs inside the caller's transaction; the ``entry_number`` unique
        constraint is the final guard against any concurrent collision.
        """
        year = entry_date.year
        prefix = f"JE-{year}-"
        count = await self._session.scalar(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.entry_number.like(f"{prefix}%"))
        )
        return f"{prefix}{(count or 0) + 1:06d}"

    # -- core entry construction --------------------------------------------

    async def _create_entry(
        self,
        *,
        entry_date: date,
        description: str,
        specs: Sequence[_LineSpec],
        source: EntrySource,
        status: EntryStatus,
        reference: str | None = None,
        reversed_entry_id: uuid.UUID | None = None,
    ) -> JournalEntry:
        """Build, balance-check, and flush a journal entry from line specs.

        Enforces the double-entry invariant (≥ 2 lines, debits == credits)
        before writing anything. Returns the flushed entry with lines loaded.
        """
        if len(specs) < 2:
            raise ValidationError("An entry must have at least two lines.")

        total_debit = _money(sum((s.debit for s in specs), Decimal("0")))
        total_credit = _money(sum((s.credit for s in specs), Decimal("0")))
        if total_debit != total_credit:
            raise ValidationError(
                f"Entry is unbalanced: debits {total_debit} != "
                f"credits {total_credit}."
            )
        if total_debit <= 0:
            raise ValidationError("Entry total must be greater than zero.")

        entry = JournalEntry(
            entry_number=await self._next_entry_number(entry_date),
            entry_date=entry_date,
            description=description,
            source=source,
            status=status,
            reference=reference,
            reversed_entry_id=reversed_entry_id,
            lines=[
                JournalLine(
                    account_id=s.account.id,
                    debit=_money(s.debit),
                    credit=_money(s.credit),
                    memo=s.memo,
                )
                for s in specs
            ],
        )
        self._session.add(entry)
        await self._session.flush()
        return await self._reload(entry.id)

    async def _reload(self, entry_id: uuid.UUID) -> JournalEntry:
        """Reload an entry with lines and their accounts eagerly loaded."""
        result = await self._session.execute(
            select(JournalEntry)
            .where(JournalEntry.id == entry_id)
            .options(selectinload(JournalEntry.lines).selectinload(JournalLine.account))
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            raise NotFoundError(f"Entry {entry_id} does not exist.")
        return entry

    # -- transaction templates ----------------------------------------------

    async def create_owner_capital_entry(
        self, data: OwnerCapitalCreate
    ) -> JournalEntry:
        """Owner investment: Dr Cash/Bank · Cr Owner Capital (3000)."""
        deposit = await self._get_account(
            data.deposit_account_id, allowed_types=[AccountType.ASSET]
        )
        capital = await self._get_account_by_code(CODE_OWNER_CAPITAL)
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(deposit, data.amount, Decimal("0"), data.memo),
                _LineSpec(capital, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    async def create_income_entry(self, data: IncomeCreate) -> JournalEntry:
        """Cash income: Dr Cash/Bank · Cr Revenue."""
        deposit = await self._get_account(
            data.deposit_account_id, allowed_types=[AccountType.ASSET]
        )
        revenue = await self._get_account(
            data.revenue_account_id, allowed_types=[AccountType.REVENUE]
        )
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(deposit, data.amount, Decimal("0"), data.memo),
                _LineSpec(revenue, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    async def create_expense_entry(self, data: ExpenseCreate) -> JournalEntry:
        """Paid expense: Dr Expense · Cr Cash/Bank."""
        expense = await self._get_account(
            data.expense_account_id, allowed_types=[AccountType.EXPENSE]
        )
        paid_from = await self._get_account(
            data.paid_from_account_id, allowed_types=[AccountType.ASSET]
        )
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(expense, data.amount, Decimal("0"), data.memo),
                _LineSpec(paid_from, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    async def create_vendor_bill(self, data: VendorBillCreate) -> JournalEntry:
        """Vendor bill: Dr Expense/Asset · Cr Accounts Payable (2000)."""
        target = await self._get_account(
            data.expense_or_asset_account_id,
            allowed_types=[AccountType.EXPENSE, AccountType.ASSET],
        )
        payable = await self._get_account_by_code(CODE_ACCOUNTS_PAYABLE)
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(target, data.amount, Decimal("0"), data.memo),
                _LineSpec(payable, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    async def record_vendor_payment(self, data: VendorPaymentCreate) -> JournalEntry:
        """Vendor payment: Dr Accounts Payable (2000) · Cr Cash/Bank."""
        payable = await self._get_account_by_code(CODE_ACCOUNTS_PAYABLE)
        paid_from = await self._get_account(
            data.paid_from_account_id, allowed_types=[AccountType.ASSET]
        )
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(payable, data.amount, Decimal("0"), data.memo),
                _LineSpec(paid_from, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    async def create_owner_withdrawal(
        self, data: OwnerWithdrawalCreate
    ) -> JournalEntry:
        """Owner withdrawal: Dr Owner Drawings (3100) · Cr Cash/Bank."""
        drawings = await self._get_account_by_code(CODE_OWNER_DRAWINGS)
        paid_from = await self._get_account(
            data.paid_from_account_id, allowed_types=[AccountType.ASSET]
        )
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(drawings, data.amount, Decimal("0"), data.memo),
                _LineSpec(paid_from, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    async def transfer_funds(self, data: TransferCreate) -> JournalEntry:
        """Fund transfer: Dr destination Cash/Bank · Cr source Cash/Bank."""
        if data.from_account_id == data.to_account_id:
            raise ValidationError("Transfer source and destination must differ.")
        source_acct = await self._get_account(
            data.from_account_id, allowed_types=[AccountType.ASSET]
        )
        dest_acct = await self._get_account(
            data.to_account_id, allowed_types=[AccountType.ASSET]
        )
        return await self._create_entry(
            entry_date=data.date,
            description=data.description,
            specs=[
                _LineSpec(dest_acct, data.amount, Decimal("0"), data.memo),
                _LineSpec(source_acct, Decimal("0"), data.amount, data.memo),
            ],
            source=EntrySource.MANUAL,
            status=EntryStatus.POSTED,
        )

    # -- update / post / reverse --------------------------------------------

    async def update_draft_entry(
        self, entry_id: uuid.UUID, data: EntryUpdate
    ) -> JournalEntry:
        """Edit a DRAFT entry. POSTED/REVERSED entries are immutable → 409."""
        entry = await self._reload(entry_id)
        if entry.status is not EntryStatus.DRAFT:
            raise ConflictError(
                f"Entry {entry.entry_number} is {entry.status.value} and cannot "
                "be edited; reverse it and post a correction instead."
            )

        if data.description is not None:
            entry.description = data.description
        if data.entry_date is not None:
            entry.entry_date = data.entry_date
        if data.reference is not None:
            entry.reference = data.reference

        if data.lines is not None:
            specs: list[_LineSpec] = []
            for line in data.lines:
                account = await self._get_account(line.account_id)
                specs.append(
                    _LineSpec(
                        account,
                        _money(line.debit) if line.debit is not None else Decimal("0"),
                        _money(line.credit)
                        if line.credit is not None
                        else Decimal("0"),
                        line.memo,
                    )
                )
            total_debit = _money(sum((s.debit for s in specs), Decimal("0")))
            total_credit = _money(sum((s.credit for s in specs), Decimal("0")))
            if total_debit != total_credit:
                raise ValidationError(
                    f"Entry is unbalanced: debits {total_debit} != "
                    f"credits {total_credit}."
                )
            if total_debit <= 0:
                raise ValidationError("Entry total must be greater than zero.")
            entry.lines = [
                JournalLine(
                    account_id=s.account.id,
                    debit=s.debit,
                    credit=s.credit,
                    memo=s.memo,
                )
                for s in specs
            ]

        await self._session.flush()
        return await self._reload(entry.id)

    async def post_entry(self, entry_id: uuid.UUID) -> JournalEntry:
        """Transition a DRAFT entry to POSTED after re-checking its balance."""
        entry = await self._reload(entry_id)
        if entry.status is EntryStatus.POSTED:
            raise ConflictError(
                f"Entry {entry.entry_number} is already posted."
            )
        if entry.status is EntryStatus.REVERSED:
            raise ConflictError(
                f"Entry {entry.entry_number} is reversed and cannot be posted."
            )
        if len(entry.lines) < 2:
            raise ValidationError("An entry must have at least two lines.")
        if _money(entry.total_debit) != _money(entry.total_credit):
            raise ValidationError(
                "Entry is unbalanced; debits must equal credits before posting."
            )
        entry.status = EntryStatus.POSTED
        await self._session.flush()
        return await self._reload(entry.id)

    async def reverse_posted_entry(
        self, entry_id: uuid.UUID, *, reason: str | None = None
    ) -> JournalEntry:
        """Reverse a POSTED entry.

        Creates a new entry with swapped debit/credit lines, links it to the
        original via ``reversed_entry_id``, and marks the original REVERSED.
        DRAFT or already-REVERSED originals are rejected with 409.
        """
        original = await self._reload(entry_id)
        if original.status is EntryStatus.DRAFT:
            raise ConflictError(
                f"Entry {original.entry_number} is a draft; there is nothing "
                "posted to reverse."
            )
        if original.status is EntryStatus.REVERSED:
            raise ConflictError(
                f"Entry {original.entry_number} has already been reversed."
            )

        specs = [
            _LineSpec(
                account=line.account,
                debit=line.credit,
                credit=line.debit,
                memo=line.memo,
            )
            for line in original.lines
        ]
        description = f"Reversal of {original.entry_number}"
        if reason:
            description = f"{description}: {reason}"
        reversal = await self._create_entry(
            entry_date=original.entry_date,
            description=description,
            specs=specs,
            source=EntrySource.SYSTEM,
            status=EntryStatus.POSTED,
            reference=original.entry_number,
            reversed_entry_id=original.id,
        )
        original.status = EntryStatus.REVERSED
        await self._session.flush()
        return await self._reload(reversal.id)

    # -- reads ---------------------------------------------------------------

    async def get_entry(self, entry_id: uuid.UUID) -> JournalEntry:
        """Return one entry with lines/accounts loaded (404 if missing)."""
        return await self._reload(entry_id)

    async def search_entries(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        account_id: uuid.UUID | None = None,
        source: EntrySource | None = None,
        status: EntryStatus | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JournalEntry], int]:
        """Filtered, paginated entry search. Returns ``(items, total)``."""
        conditions = []
        if start is not None:
            conditions.append(JournalEntry.entry_date >= start)
        if end is not None:
            conditions.append(JournalEntry.entry_date <= end)
        if source is not None:
            conditions.append(JournalEntry.source == source)
        if status is not None:
            conditions.append(JournalEntry.status == status)
        if account_id is not None:
            conditions.append(
                JournalEntry.lines.any(JournalLine.account_id == account_id)
            )
        if query:
            like = f"%{query}%"
            conditions.append(
                or_(
                    JournalEntry.description.ilike(like),
                    JournalEntry.reference.ilike(like),
                    JournalEntry.entry_number.ilike(like),
                )
            )

        total = await self._session.scalar(
            select(func.count()).select_from(JournalEntry).where(*conditions)
        )
        result = await self._session.execute(
            select(JournalEntry)
            .where(*conditions)
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_number.desc())
            .limit(limit)
            .offset(offset)
            .options(
                selectinload(JournalEntry.lines).selectinload(JournalLine.account)
            )
        )
        return list(result.scalars().all()), (total or 0)

    async def list_accounts(
        self,
        *,
        type_: AccountType | None = None,
        is_active: bool | None = None,
    ) -> list[Account]:
        """List accounts, optionally filtered by type and active flag."""
        conditions = []
        if type_ is not None:
            conditions.append(Account.type == type_)
        if is_active is not None:
            conditions.append(Account.is_active == is_active)
        result = await self._session.execute(
            select(Account).where(*conditions).order_by(Account.code)
        )
        return list(result.scalars().all())

    async def create_account(self, data: AccountCreate) -> Account:
        """Create a chart-of-accounts account (unique code enforced)."""
        existing = await self._session.execute(
            select(Account).where(Account.code == data.code)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Account code {data.code} already exists.")
        account = Account(code=data.code, name=data.name, type=data.type)
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account
