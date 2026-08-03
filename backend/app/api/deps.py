"""Shared FastAPI dependencies for the API layer.

Provides the request-scoped :class:`AccountingService`. The service is bound to
the same ``AsyncSession`` that routes inject via :func:`get_session`, so a route
can call service methods (which flush but never commit) and then commit the unit
of work exactly once. FastAPI caches ``get_session`` within a request, so the
service and the route share one session and one transaction.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.accounting import AccountingService
from app.services.reports import ReportService


async def get_accounting_service(
    session: AsyncSession = Depends(get_session),
) -> AccountingService:
    """Return an :class:`AccountingService` bound to the request session."""
    return AccountingService(session)


async def get_report_service(
    session: AsyncSession = Depends(get_session),
) -> ReportService:
    """Return a read-only :class:`ReportService` bound to the request session."""
    return ReportService(session)
