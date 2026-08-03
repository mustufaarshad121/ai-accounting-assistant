"""accounting core: enums, accounts, journal_entries, journal_lines

Revision ID: 0001_accounting_core
Revises:
Create Date: 2026-01-16

Hand-authored initial migration for the accounting-core feature branch. Creates
the three PostgreSQL native ENUM types and the three ledger tables with all
foreign keys, indexes, the unique constraints on ``accounts.code`` and
``journal_entries.entry_number``, and the per-line monetary CHECK constraints
(debit/credit non-negative; exactly one side positive). The downgrade reverses
everything in dependency order, including dropping the ENUM types.

This migration is limited to the accounting-core scope. The reports (audit_runs,
audit_findings), ai-agent (chat_threads, chat_messages, agent_tool_calls), and
auth (profiles) tables are introduced by their own migrations on their own
feature branches — see specs/03-database-schema.md (phased migrations).

NOTE: statically authored and validated only; NOT yet applied to any live
PostgreSQL database. Runtime application to Supabase is PENDING explicit
approval.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_accounting_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ENUM types. create_type=False on the columns below: we create/drop the types
# explicitly so the migration is symmetric and does not rely on implicit
# checkfirst behavior during table creation.
account_type = postgresql.ENUM(
    "ASSET",
    "LIABILITY",
    "EQUITY",
    "REVENUE",
    "EXPENSE",
    name="account_type",
    create_type=False,
)
entry_source = postgresql.ENUM(
    "MANUAL",
    "AI",
    "SYSTEM",
    "IMPORT",
    name="entry_source",
    create_type=False,
)
entry_status = postgresql.ENUM(
    "DRAFT",
    "POSTED",
    "REVERSED",
    name="entry_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. ENUM types (must exist before the columns that reference them).
    account_type.create(bind, checkfirst=True)
    entry_source.create(bind, checkfirst=True)
    entry_status.create(bind, checkfirst=True)

    # 2. accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", account_type, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_code", "accounts", ["code"], unique=True)
    op.create_index("ix_accounts_type", "accounts", ["type"], unique=False)

    # 3. journal_entries (self-referential FK for reversals).
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entry_number", sa.String(length=32), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", entry_source, nullable=False),
        sa.Column("status", entry_status, nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("reversed_entry_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["reversed_entry_id"],
            ["journal_entries.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journal_entries_entry_number",
        "journal_entries",
        ["entry_number"],
        unique=True,
    )
    op.create_index(
        "ix_journal_entries_entry_date", "journal_entries", ["entry_date"]
    )
    op.create_index("ix_journal_entries_status", "journal_entries", ["status"])
    op.create_index(
        "ix_journal_entries_reversed_entry_id",
        "journal_entries",
        ["reversed_entry_id"],
    )

    # 4. journal_lines (per-row monetary CHECK constraints live here).
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journal_entry_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("debit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("credit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.CheckConstraint("debit >= 0", name="ck_journal_lines_debit_non_negative"),
        sa.CheckConstraint(
            "credit >= 0", name="ck_journal_lines_credit_non_negative"
        ),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0)",
            name="ck_journal_lines_exactly_one_side",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journal_lines_journal_entry_id",
        "journal_lines",
        ["journal_entry_id"],
    )
    op.create_index(
        "ix_journal_lines_account_id", "journal_lines", ["account_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Reverse dependency order: lines -> entries -> accounts -> enum types.
    op.drop_index("ix_journal_lines_account_id", table_name="journal_lines")
    op.drop_index("ix_journal_lines_journal_entry_id", table_name="journal_lines")
    op.drop_table("journal_lines")

    op.drop_index(
        "ix_journal_entries_reversed_entry_id", table_name="journal_entries"
    )
    op.drop_index("ix_journal_entries_status", table_name="journal_entries")
    op.drop_index("ix_journal_entries_entry_date", table_name="journal_entries")
    op.drop_index(
        "ix_journal_entries_entry_number", table_name="journal_entries"
    )
    op.drop_table("journal_entries")

    op.drop_index("ix_accounts_type", table_name="accounts")
    op.drop_index("ix_accounts_code", table_name="accounts")
    op.drop_table("accounts")

    entry_status.drop(bind, checkfirst=True)
    entry_source.drop(bind, checkfirst=True)
    account_type.drop(bind, checkfirst=True)
