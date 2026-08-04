"""Deterministic financial reporting service.

Every figure here is computed in plain Python from PostgreSQL data using
:class:`~decimal.Decimal` arithmetic — never float, and never by an LLM. The
four reports are:

* **Trial balance** (as of a date) — each account's net balance on its natural
  side; total debits must equal total credits.
* **Profit & loss** (over a period) — revenue less expenses.
* **Balance sheet** (as of a date) — assets = liabilities + equity, where
  equity folds in current-period earnings so the accounting equation holds.
* **Automated Monthly Accounting Review** — a set of internal
  consistency/quality checks (INFO / WARNING / CRITICAL). This is **not** a
  statutory or external audit and produces **no** formal audit opinion.

Status scope for financial figures
-----------------------------------
Reports include entries whose status is **POSTED or REVERSED**, and exclude
**DRAFT**. A reversed original entry stays in the ledger and is offset by its
posted reversal (equal and opposite), so the two net to zero — dropping the
REVERSED original would leave the reversal standing alone and distort every
total. DRAFT entries are not part of financial figures.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.enums import AccountType, EntrySource, EntryStatus
from app.models.journal import JournalEntry, JournalLine
from app.schemas.report import (
    AmountRow,
    BalanceRow,
    BalanceSheetOut,
    EquitySection,
    MonthlyReviewOut,
    ProfitLossOut,
    ReviewFinding,
    TrialBalanceOut,
    TrialBalanceRow,
)

# Equity account codes (from the seeded chart of accounts).
CODE_OWNER_DRAWINGS = "3100"

# Entries counted in financial figures: everything ever posted (POSTED plus the
# terminal REVERSED originals), excluding editable DRAFTs.
_INCLUDED_STATUSES = (EntryStatus.POSTED, EntryStatus.REVERSED)

MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0.00")

# Monthly-review thresholds for the "unusually large transaction" heuristic.
LARGE_ABS_THRESHOLD = Decimal("1000000.00")
LARGE_MEAN_MULTIPLIER = Decimal("10")
LARGE_MEAN_MIN_SAMPLE = 5

_SEVERITY_RANK = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}


def _money(value: Decimal) -> Decimal:
    """Quantize to two decimal places (never float)."""
    return value.quantize(MONEY_QUANTUM)


def _to_decimal(value: object) -> Decimal:
    """Coerce a SQL aggregate result to Decimal without binary-float drift."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value if value is not None else "0"))


class ReportService:
    """Read-only, deterministic report computations for one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- shared aggregation --------------------------------------------------

    async def _balances(
        self,
        *,
        upto: date | None = None,
        start: date | None = None,
        end: date | None = None,
        types: Sequence[AccountType] | None = None,
    ) -> list[tuple[Account, Decimal, Decimal]]:
        """Per-account (sum_debit, sum_credit) over the included statuses.

        Filters by an as-of date (``upto``) or a ``[start, end]`` window, and
        optionally by account type. Only accounts with ledger activity in scope
        are returned.
        """
        stmt = (
            select(
                Account,
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            )
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.status.in_(_INCLUDED_STATUSES))
            .group_by(Account.id)
        )
        if upto is not None:
            stmt = stmt.where(JournalEntry.entry_date <= upto)
        if start is not None:
            stmt = stmt.where(JournalEntry.entry_date >= start)
        if end is not None:
            stmt = stmt.where(JournalEntry.entry_date <= end)
        if types is not None:
            stmt = stmt.where(Account.type.in_(list(types)))

        result = await self._session.execute(stmt)
        return [
            (acct, _money(_to_decimal(d)), _money(_to_decimal(c)))
            for acct, d, c in result.all()
        ]

    # -- trial balance -------------------------------------------------------

    async def trial_balance(self, as_of: date) -> TrialBalanceOut:
        """Net each account onto its natural side as of ``as_of``."""
        rows: list[TrialBalanceRow] = []
        total_debit = ZERO
        total_credit = ZERO

        for account, debit, credit in await self._balances(upto=as_of):
            net = debit - credit
            if net == 0:
                continue
            if net > 0:
                dr, cr = net, ZERO
            else:
                dr, cr = ZERO, -net
            total_debit += dr
            total_credit += cr
            rows.append(
                TrialBalanceRow(
                    account_code=account.code,
                    account_name=account.name,
                    account_type=account.type,
                    debit_balance=dr,
                    credit_balance=cr,
                )
            )

        rows.sort(key=lambda r: r.account_code)
        return TrialBalanceOut(
            as_of=as_of,
            rows=rows,
            total_debit=_money(total_debit),
            total_credit=_money(total_credit),
            balanced=_money(total_debit) == _money(total_credit),
        )

    # -- profit & loss -------------------------------------------------------

    async def profit_and_loss(self, start: date, end: date) -> ProfitLossOut:
        """Revenue (credit-normal) less expenses (debit-normal) over a period."""
        revenue_rows: list[AmountRow] = []
        expense_rows: list[AmountRow] = []
        total_revenue = ZERO
        total_expenses = ZERO

        for account, debit, credit in await self._balances(
            start=start, end=end, types=[AccountType.REVENUE]
        ):
            amount = credit - debit  # revenue is credit-normal
            if amount == 0:
                continue
            total_revenue += amount
            revenue_rows.append(
                AmountRow(
                    account_code=account.code,
                    account_name=account.name,
                    amount=amount,
                )
            )

        for account, debit, credit in await self._balances(
            start=start, end=end, types=[AccountType.EXPENSE]
        ):
            amount = debit - credit  # expense is debit-normal
            if amount == 0:
                continue
            total_expenses += amount
            expense_rows.append(
                AmountRow(
                    account_code=account.code,
                    account_name=account.name,
                    amount=amount,
                )
            )

        revenue_rows.sort(key=lambda r: r.account_code)
        expense_rows.sort(key=lambda r: r.account_code)
        return ProfitLossOut(
            start=start,
            end=end,
            revenue=revenue_rows,
            expenses=expense_rows,
            total_revenue=_money(total_revenue),
            total_expenses=_money(total_expenses),
            net_profit=_money(total_revenue - total_expenses),
        )

    # -- balance sheet -------------------------------------------------------

    async def balance_sheet(self, as_of: date) -> BalanceSheetOut:
        """Assets = liabilities + equity (incl. current-period earnings)."""
        asset_rows: list[BalanceRow] = []
        liability_rows: list[BalanceRow] = []
        total_assets = ZERO
        total_liabilities = ZERO

        for account, debit, credit in await self._balances(
            upto=as_of, types=[AccountType.ASSET]
        ):
            amount = debit - credit  # asset is debit-normal
            if amount == 0:
                continue
            total_assets += amount
            asset_rows.append(
                BalanceRow(
                    account_code=account.code,
                    account_name=account.name,
                    amount=amount,
                )
            )

        for account, debit, credit in await self._balances(
            upto=as_of, types=[AccountType.LIABILITY]
        ):
            amount = credit - debit  # liability is credit-normal
            if amount == 0:
                continue
            total_liabilities += amount
            liability_rows.append(
                BalanceRow(
                    account_code=account.code,
                    account_name=account.name,
                    amount=amount,
                )
            )

        # Equity accounts: owner capital (credit-normal) and owner drawings
        # (a contra-equity account carrying a debit balance).
        owner_capital = ZERO
        owner_drawings = ZERO
        for account, debit, credit in await self._balances(
            upto=as_of, types=[AccountType.EQUITY]
        ):
            if account.code == CODE_OWNER_DRAWINGS:
                owner_drawings += debit - credit  # debit-normal contra account
            else:
                owner_capital += credit - debit  # credit-normal

        # Current-period earnings (retained earnings): all revenue less all
        # expenses up to the as-of date. There is no closing entry in the MVP,
        # so earnings are recognized directly into equity here.
        earnings = ZERO
        for _account, debit, credit in await self._balances(
            upto=as_of, types=[AccountType.REVENUE]
        ):
            earnings += credit - debit
        for _account, debit, credit in await self._balances(
            upto=as_of, types=[AccountType.EXPENSE]
        ):
            earnings -= debit - credit

        total_equity = owner_capital - owner_drawings + earnings
        total_liabilities_and_equity = total_liabilities + total_equity

        asset_rows.sort(key=lambda r: r.account_code)
        liability_rows.sort(key=lambda r: r.account_code)
        return BalanceSheetOut(
            as_of=as_of,
            assets=asset_rows,
            liabilities=liability_rows,
            equity=EquitySection(
                owner_capital=_money(owner_capital),
                owner_drawings=_money(owner_drawings),
                current_period_earnings=_money(earnings),
                total_equity=_money(total_equity),
            ),
            total_assets=_money(total_assets),
            total_liabilities_and_equity=_money(total_liabilities_and_equity),
            balanced=_money(total_assets) == _money(total_liabilities_and_equity),
        )

    # -- automated monthly accounting review --------------------------------

    async def monthly_review(
        self, *, start: date, end: date, today: date
    ) -> MonthlyReviewOut:
        """Run internal consistency/quality checks over ``[start, end]``.

        NOT a statutory or external audit and NOT a formal audit opinion — an
        automated set of heuristics that surface entries a human should look at.
        ``today`` anchors the future-dated check (supplied by the caller so the
        computation stays deterministic and testable).
        """
        result = await self._session.execute(
            select(JournalEntry)
            .where(
                JournalEntry.entry_date >= start,
                JournalEntry.entry_date <= end,
                JournalEntry.status.in_(_INCLUDED_STATUSES),
            )
            .options(
                selectinload(JournalEntry.lines).selectinload(JournalLine.account)
            )
            .order_by(JournalEntry.entry_date, JournalEntry.entry_number)
        )
        entries = list(result.scalars().all())
        findings: list[ReviewFinding] = []

        def add(
            rule: str,
            severity: str,
            message: str,
            entry: JournalEntry | None = None,
            details: dict | None = None,
        ) -> None:
            findings.append(
                ReviewFinding(
                    rule_code=rule,
                    severity=severity,
                    message=message,
                    entry_id=str(entry.id) if entry is not None else None,
                    entry_number=entry.entry_number if entry is not None else None,
                    details=details,
                )
            )

        # Precompute per-entry totals and the mean for the large-txn heuristic.
        totals: dict[uuid.UUID, tuple[Decimal, Decimal]] = {}
        for e in entries:
            td = _money(sum((ln.debit for ln in e.lines), ZERO))
            tc = _money(sum((ln.credit for ln in e.lines), ZERO))
            totals[e.id] = (td, tc)
        amounts = [td for td, _tc in totals.values()]
        mean_amount = (
            _money(sum(amounts, ZERO) / Decimal(len(amounts))) if amounts else ZERO
        )

        # Duplicate detection groups non-reversal entries by date/description/amount.
        dup_groups: dict[tuple, list[JournalEntry]] = defaultdict(list)

        for e in entries:
            td, tc = totals[e.id]

            # 1. Unbalanced entry (integrity guard; service normally prevents).
            if td != tc:
                add(
                    "UNBALANCED_ENTRY",
                    "CRITICAL",
                    f"Entry {e.entry_number} is unbalanced (debits {td} != credits {tc}).",
                    e,
                    {"total_debit": str(td), "total_credit": str(tc)},
                )

            # 2. Zero-value entry.
            if td == 0 and tc == 0:
                add(
                    "ZERO_VALUE_ENTRY",
                    "CRITICAL",
                    f"Entry {e.entry_number} has a zero total value.",
                    e,
                )

            # 3. Negative line values.
            if any(ln.debit < 0 or ln.credit < 0 for ln in e.lines):
                add(
                    "NEGATIVE_LINE_VALUE",
                    "CRITICAL",
                    f"Entry {e.entry_number} contains a negative debit or credit.",
                    e,
                )

            # 4. Missing / blank description.
            if not e.description or not e.description.strip():
                add(
                    "MISSING_DESCRIPTION",
                    "WARNING",
                    f"Entry {e.entry_number} has no description.",
                    e,
                )

            # 5. Missing reference (traceability aid).
            if e.reference is None or not str(e.reference).strip():
                add(
                    "MISSING_REFERENCE",
                    "INFO",
                    f"Entry {e.entry_number} has no reference.",
                    e,
                )

            # 6. Future-dated entry.
            if e.entry_date > today:
                add(
                    "FUTURE_DATED_ENTRY",
                    "WARNING",
                    f"Entry {e.entry_number} is dated {e.entry_date}, after today ({today}).",
                    e,
                    {"entry_date": str(e.entry_date), "today": str(today)},
                )

            # 7. Unusually large transaction.
            is_large_abs = td > LARGE_ABS_THRESHOLD
            is_large_rel = (
                len(amounts) >= LARGE_MEAN_MIN_SAMPLE
                and mean_amount > 0
                and td > mean_amount * LARGE_MEAN_MULTIPLIER
            )
            if is_large_abs or is_large_rel:
                add(
                    "LARGE_TRANSACTION",
                    "INFO",
                    f"Entry {e.entry_number} amount {td} is unusually large.",
                    e,
                    {"amount": str(td), "period_mean": str(mean_amount)},
                )

            # 9 & 10. Revenue debited / expense credited outside a reversal.
            if e.source is not EntrySource.SYSTEM:
                for ln in e.lines:
                    if ln.account.type is AccountType.REVENUE and ln.debit > 0:
                        add(
                            "REVENUE_ACCOUNT_DEBITED",
                            "WARNING",
                            f"Entry {e.entry_number} debits revenue account "
                            f"{ln.account.code} outside a reversal.",
                            e,
                            {"account_code": ln.account.code, "debit": str(ln.debit)},
                        )
                    if ln.account.type is AccountType.EXPENSE and ln.credit > 0:
                        add(
                            "EXPENSE_ACCOUNT_CREDITED",
                            "WARNING",
                            f"Entry {e.entry_number} credits expense account "
                            f"{ln.account.code} outside a reversal.",
                            e,
                            {"account_code": ln.account.code, "credit": str(ln.credit)},
                        )

            # 8 (deferred to here). Duplicate-looking grouping key.
            if e.reversed_entry_id is None:
                key = (e.entry_date, (e.description or "").strip().lower(), td)
                dup_groups[key].append(e)

            # 11. Reversal consistency.
            if e.reversed_entry_id is not None:
                await self._check_reversal(e, td, add)
            if e.status is EntryStatus.REVERSED:
                referencing = await self._session.scalar(
                    select(func.count())
                    .select_from(JournalEntry)
                    .where(JournalEntry.reversed_entry_id == e.id)
                )
                if not referencing:
                    add(
                        "REVERSAL_MISSING",
                        "CRITICAL",
                        f"Entry {e.entry_number} is REVERSED but no reversal "
                        "entry references it.",
                        e,
                    )

        # 8. Emit duplicate findings for groups with more than one entry.
        for group in dup_groups.values():
            if len(group) > 1:
                numbers = ", ".join(g.entry_number for g in group)
                for g in group:
                    add(
                        "DUPLICATE_ENTRY",
                        "WARNING",
                        f"Entry {g.entry_number} looks like a duplicate "
                        f"(same date, description, and amount as: {numbers}).",
                        g,
                        {"group": numbers},
                    )

        findings.sort(
            key=lambda f: (_SEVERITY_RANK.get(f.severity, 99), f.rule_code, f.entry_number or "")
        )

        counts = {"INFO": 0, "WARNING": 0, "CRITICAL": 0}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        summary = (
            f"Automated Monthly Accounting Review of {len(entries)} entr"
            f"{'y' if len(entries) == 1 else 'ies'} for {start} to {end}: "
            f"{counts['CRITICAL']} critical, {counts['WARNING']} warning, "
            f"{counts['INFO']} info finding(s). This is an automated internal "
            f"review, not a statutory or external audit."
        )

        return MonthlyReviewOut(
            period_start=start,
            period_end=end,
            findings=findings,
            counts_by_severity=counts,
            summary=summary,
        )

    async def _check_reversal(
        self, reversal: JournalEntry, reversal_total: Decimal, add
    ) -> None:
        """Validate a reversal entry against its original."""
        original = await self._session.get(JournalEntry, reversal.reversed_entry_id)
        if original is None:
            add(
                "REVERSAL_TARGET_MISSING",
                "CRITICAL",
                f"Reversal {reversal.entry_number} references a missing original entry.",
                reversal,
            )
            return
        if original.status is not EntryStatus.REVERSED:
            add(
                "REVERSAL_TARGET_NOT_REVERSED",
                "CRITICAL",
                f"Reversal {reversal.entry_number} targets entry "
                f"{original.entry_number}, which is {original.status.value}, "
                "not REVERSED.",
                reversal,
            )
        original_total = _money(
            _to_decimal(
                await self._session.scalar(
                    select(func.coalesce(func.sum(JournalLine.debit), 0)).where(
                        JournalLine.journal_entry_id == original.id
                    )
                )
            )
        )
        if original_total != reversal_total:
            add(
                "REVERSAL_AMOUNT_MISMATCH",
                "WARNING",
                f"Reversal {reversal.entry_number} total {reversal_total} does "
                f"not match original {original.entry_number} total {original_total}.",
                reversal,
                {"reversal_total": str(reversal_total), "original_total": str(original_total)},
            )
