"""Clock helper.

Centralizes "now"/"today" so date-dependent behavior (report defaults, the
monthly-review future-dated check) reads from one place and can be reasoned
about. Reports compute figures deterministically from ledger dates; only the
default date range and the future-dated heuristic depend on the wall clock.
"""

from __future__ import annotations

from datetime import UTC, date, datetime


def today() -> date:
    """Return the current UTC date."""
    return datetime.now(UTC).date()
