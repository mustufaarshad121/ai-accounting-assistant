"""ORM models package.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and ``create_all`` see the full schema. Import models from here
rather than reaching into submodules.
"""

from __future__ import annotations

from app.models.account import Account
from app.models.enums import AccountType, EntrySource, EntryStatus
from app.models.journal import JournalEntry, JournalLine

__all__ = [
    "Account",
    "AccountType",
    "EntrySource",
    "EntryStatus",
    "JournalEntry",
    "JournalLine",
]
