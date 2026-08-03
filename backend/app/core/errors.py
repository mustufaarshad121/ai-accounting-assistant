"""Structured API error foundation.

Provides a small hierarchy of application errors and an exception handler that
renders them as consistent JSON: ``{"detail": ..., "code": ...}``. Feature
branches raise these (or subclasses) from the service layer; routes stay thin.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for structured application errors.

    Attributes:
        message: Human-readable error description (goes into ``detail``).
        status_code: HTTP status code to return.
        code: Stable machine-readable error code.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    """Request conflicts with the current state (e.g. immutable resource)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(AppError):
    """Business-rule validation failed (beyond Pydantic edge validation)."""

    status_code = 422  # Unprocessable Content
    code = "validation_error"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the structured ``AppError`` handler to the FastAPI app."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )
