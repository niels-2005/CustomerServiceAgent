"""Shared API error types and exception handlers.

The handlers normalize framework, validation, rate-limit, and unexpected errors
into one response envelope so clients can rely on a stable contract.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ApiError(Exception):
    """Application-level API error with an explicit HTTP mapping."""

    code: str
    message: str
    status_code: int
    details: list[dict[str, Any]] = field(default_factory=list)


def get_request_id(request: Request) -> str:
    """Return the request ID stored by middleware or a safe fallback."""
    request_id = getattr(request.state, "request_id", "")
    if request_id:
        return request_id
    return "unknown"


def error_response(
    *,
    request_id: str,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Build the standard error response envelope used by the API."""
    error_payload: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details:
        error_payload["details"] = details

    payload: dict[str, Any] = {
        "error": error_payload,
        "request_id": request_id,
    }
    return JSONResponse(status_code=status_code, content=payload)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Render an ``ApiError`` with the standard response shape."""
    return error_response(
        request_id=get_request_id(request),
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render FastAPI validation errors in the standard response shape."""
    details = [
        {
            "type": error["type"],
            "loc": [str(part) for part in error["loc"]],
            "msg": error["msg"],
        }
        for error in exc.errors()
    ]
    return error_response(
        request_id=get_request_id(request),
        status_code=422,
        code="invalid_request",
        message="Request validation failed.",
        details=details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalize Starlette HTTP exceptions into the API error contract."""
    try:
        status = HTTPStatus(exc.status_code)
        code = status.phrase.lower().replace(" ", "_")
    except ValueError:
        code = "http_error"

    message = str(exc.detail) if exc.detail else "HTTP request failed."
    details = exc.detail if isinstance(exc.detail, list) else None
    return error_response(
        request_id=get_request_id(request),
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Render rate-limit errors while logging request context."""
    logger.warning(
        "Rate limit exceeded request_id=%s path=%s method=%s",
        get_request_id(request),
        request.url.path,
        request.method,
    )
    return error_response(
        request_id=get_request_id(request),
        status_code=429,
        code="rate_limit_exceeded",
        message=str(exc.detail),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render unexpected exceptions without leaking internal details."""
    logger.exception(
        "Unhandled API exception request_id=%s path=%s method=%s",
        get_request_id(request),
        request.url.path,
        request.method,
        exc_info=exc,
    )
    return error_response(
        request_id=get_request_id(request),
        status_code=500,
        code="internal_server_error",
        message="Internal server error.",
    )
