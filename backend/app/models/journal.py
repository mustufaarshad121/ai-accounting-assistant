"""Journal entry and journal line ORM models (double-entry ledger).

A ``JournalEntry`` groups two or more ``JournalLine`` rows. Each line touches
one account on exactly one side (debit XOR credit, strictly positive). The
cross-row invariant — total debits == total credits — cannot be expressed as a
single-row CHECK, so it is enforced transactionally in the service layer; the
per-line CHECK constraints here guarantee each line is individually well-formed.
Money is ``NUMERIC(18, 2)`` mapped to :class:`~decimal.Decimal`.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EntrySource, EntryStatus
from app.models.mixins import MONEY_PRECISION, MONEY_SCALE, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account


class JournalEntry(TimestampMixin, Base):
    """A balanced group of journal lines with a lifecycle status."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Human-facing identifier, e.g. "JE-2026-000123". Unique across all entries.
    entry_number: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[EntrySource] = mapped_column(
        SAEnum(EntrySource, name="entry_source", native_enum=True),
        nullable=False,
    )
    status: Mapped[EntryStatus] = mapped_column(
        SAEnum(EntryStatus, name="entry_status", native_enum=True),
        nullable=False,
        index=True,
    )
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    # On a reversal entry, points at the original entry it reverses.
    reversed_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lines: Mapped[list[JournalLine]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.id",
    )
    # Self-referential link: the reversal entry (if any) that reverses this one.
    reversed_entry: Mapped[JournalEntry | None] = relationship(
        remote_side=[id],
        backref="reversal_entries",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<JournalEntry {self.entry_number} {self.status.value}>"


class JournalLine(Base):
    """A single debit-or-credit line against one account."""

    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0", name="ck_journal_lines_debit_non_negative"),
        CheckConstraint("credit >= 0", name="ck_journal_lines_credit_non_negative"),
        # Exactly one side positive: forbids both-positive and both-zero.
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0)",
            name="ck_journal_lines_exactly_one_side",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    debit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0"),
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0"),
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship(back_populates="lines")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<JournalLine dr={self.debit} cr={self.credit}>"
