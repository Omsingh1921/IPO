"""
Global Exception Handlers and Custom API Errors for Indian IPO Platform API (Phase 10 - Stage 4).
Translates domain, validation, and platform exceptions into uniform RFC-compliant JSON responses.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ipo_platform.db.exceptions import (
    DatabaseConnectionError,
    DuplicateIPOSlugError,
    PlatformDatabaseError,
)

logger = logging.getLogger(__name__)


def create_error_response(
    error: str,
    detail: str,
    status_code: int,
    path: str,
    extra: Dict[str, Any] = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Constructs a consistent error JSON response structure."""
    payload = {
        "error": error,
        "detail": detail,
        "status_code": status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": path,
    }
    if extra:
        payload["extra"] = extra
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handles standard FastAPI/Starlette HTTP exceptions."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return create_error_response(
        error="HTTP_EXCEPTION",
        detail=detail,
        status_code=exc.status_code,
        path=request.url.path,
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic and FastAPI input request validation errors."""
    errors = exc.errors()
    # Format details into concise readable summary
    formatted_errors = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Validation failed")
        formatted_errors.append(f"{loc}: {msg}")
    detail_msg = "; ".join(formatted_errors) if formatted_errors else "Request validation failed"

    return create_error_response(
        error="VALIDATION_ERROR",
        detail=detail_msg,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        path=request.url.path,
        extra={"validation_errors": errors},
    )


async def database_exception_handler(request: Request, exc: PlatformDatabaseError) -> JSONResponse:
    """Handles domain persistence and database errors."""
    logger.error("Database error intercepted at %s: %s", request.url.path, exc, exc_info=True)
    if isinstance(exc, DatabaseConnectionError):
        return create_error_response(
            error="DATABASE_CONNECTION_ERROR",
            detail="Database connectivity is currently unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            path=request.url.path,
        )
    if isinstance(exc, DuplicateIPOSlugError):
        return create_error_response(
            error="DUPLICATE_RESOURCE_ERROR",
            detail=str(exc),
            status_code=status.HTTP_409_CONFLICT,
            path=request.url.path,
        )
    return create_error_response(
        error="DATABASE_ERROR",
        detail="A database error occurred while processing the request",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        path=request.url.path,
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handles domain validation ValueErrors from engines."""
    logger.warning("Value error encountered at %s: %s", request.url.path, exc)
    return create_error_response(
        error="INVALID_ARGUMENT",
        detail=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST,
        path=request.url.path,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all safety net for unexpected platform exceptions."""
    logger.error("Unhandled platform exception at %s: %s", request.url.path, exc, exc_info=True)
    return create_error_response(
        error="INTERNAL_SERVER_ERROR",
        detail="An internal server error occurred while processing the request",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        path=request.url.path,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers all custom exception handlers to the FastAPI application instance."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PlatformDatabaseError, database_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
