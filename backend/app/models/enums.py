"""Accounting enumerations.

These back PostgreSQL enum types (``account_type``, ``entry_source``,
``entry_status``) and are shared by the ORM models, the service layer, and the
Pydantic schemas. Values are stored as their string names in the database.
"""

from __future__ import annotations

from enum import StrEnum


class AccountType(StrEnum):
    """Classification of an account and its normal (increasing) balance side.

    Normal balances:
        ASSET, EXPENSE  -> debit
        LIABILITY, EQUITY, REVENUE -> credit
    """

    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

    @property
    def normal_balance_is_debit(self) -> bool:
        """True if this account type normally carries a debit balance."""
        return self in (AccountType.ASSET, AccountType.EXPENSE)


class EntrySource(StrEnum):
    """Origin of a journal entry."""

    MANUAL = "MANUAL"
    AI = "AI"
    SYSTEM = "SYSTEM"
    IMPORT = "IMPORT"


class EntryStatus(StrEnum):
    """Lifecycle state of a journal entry.

    DRAFT    -> editable / deletable, not part of financial figures.
    POSTED   -> immutable; corrected only via reversal.
    REVERSED -> terminal; a reversal entry references the original.
    """

    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"
