from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from customer_bot.api.errors import (
    ApiError,
    api_error_handler,
    error_response,
    get_request_id,
    http_exception_handler,
    rate_limit_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def _build_request(*, path: str = "/chat", method: str = "POST", request_id: str | None = None):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "state": {},
    }
    request = Request(scope)
    if request_id is not None:
        request.state.request_id = request_id
    return request


@pytest.mark.unit
def test_get_request_id_returns_unknown_without_middleware_state() -> None:
    request = _build_request()

    assert get_request_id(request) == "unknown"


@pytest.mark.unit
def test_error_response_omits_details_when_not_present() -> None:
    response = error_response(
        request_id="req-1",
        status_code=400,
        code="bad_request",
        message="Bad request.",
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "error": {"code": "bad_request", "message": "Bad request."},
        "request_id": "req-1",
    }


@pytest.mark.unit
def test_api_error_handler_preserves_standard_error_contract() -> None:
    request = _build_request(request_id="req-123")
    exc = ApiError(
        code="custom_error",
        message="Something failed.",
        status_code=409,
        details=[{"field": "user_message"}],
    )

    response = asyncio.run(api_error_handler(request, exc))

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "error": {
            "code": "custom_error",
            "message": "Something failed.",
            "details": [{"field": "user_message"}],
        },
        "request_id": "req-123",
    }


@pytest.mark.unit
def test_validation_exception_handler_normalizes_pydantic_errors() -> None:
    request = _build_request(request_id="req-123")
    exc = RequestValidationError(
        [
            {
                "type": "missing",
                "loc": ("body", "user_message"),
                "msg": "Field required",
                "input": {"session_id": "abc"},
            }
        ]
    )

    response = asyncio.run(validation_exception_handler(request, exc))

    assert response.status_code == 422
    assert json.loads(response.body) == {
        "error": {
            "code": "invalid_request",
            "message": "Request validation failed.",
            "details": [
                {
                    "type": "missing",
                    "loc": ["body", "user_message"],
                    "msg": "Field required",
                }
            ],
        },
        "request_id": "req-123",
    }


@pytest.mark.unit
def test_http_exception_handler_normalizes_list_details() -> None:
    request = _build_request(request_id="req-9")
    exc = StarletteHTTPException(
        status_code=404,
        detail=[{"type": "not_found", "msg": "No such route"}],
    )

    response = asyncio.run(http_exception_handler(request, exc))

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "error": {
            "code": "not_found",
            "message": "[{'type': 'not_found', 'msg': 'No such route'}]",
            "details": [{"type": "not_found", "msg": "No such route"}],
        },
        "request_id": "req-9",
    }


@pytest.mark.unit
def test_rate_limit_exception_handler_uses_request_id_and_status_code() -> None:
    request = _build_request(request_id="req-limit")

    class FakeRateLimitExceeded:
        detail = "10/minute"

    exc = FakeRateLimitExceeded()

    response = asyncio.run(rate_limit_exception_handler(request, exc))

    assert response.status_code == 429
    assert json.loads(response.body) == {
        "error": {"code": "rate_limit_exceeded", "message": "10/minute"},
        "request_id": "req-limit",
    }


@pytest.mark.unit
def test_unhandled_exception_handler_hides_internal_details() -> None:
    request = _build_request(request_id="req-500")

    response = asyncio.run(unhandled_exception_handler(request, RuntimeError("boom")))

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "error": {
            "code": "internal_server_error",
            "message": "Internal server error.",
        },
        "request_id": "req-500",
    }
