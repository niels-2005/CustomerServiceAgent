from __future__ import annotations

import asyncio

from fastapi import Request
from fastapi.responses import Response

from customer_bot.api.middleware import request_context_middleware


def _build_request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": headers or [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
        }
    )


async def _call_next(_request: Request) -> Response:
    return Response(status_code=200)


def test_request_context_middleware_preserves_existing_request_id() -> None:
    request = _build_request(headers=[(b"x-request-id", b"req-123")])

    response = asyncio.run(request_context_middleware(request, _call_next))

    assert request.state.request_id == "req-123"
    assert response.headers["X-Request-ID"] == "req-123"


def test_request_context_middleware_generates_defensive_headers() -> None:
    request = _build_request()

    response = asyncio.run(request_context_middleware(request, _call_next))

    assert request.state.request_id
    assert response.headers["X-Request-ID"] == request.state.request_id
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
