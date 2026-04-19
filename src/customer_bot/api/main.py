from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from customer_bot.api.deps import clear_dependency_caches, get_chat_service, get_runtime_settings
from customer_bot.api.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    rate_limit_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from customer_bot.api.middleware import request_context_middleware
from customer_bot.api.rate_limit import limiter
from customer_bot.api.routes import router
from customer_bot.observability import initialize_observability


def create_lifespan(*, enable_observability: bool, run_startup_checks: bool):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_runtime_settings()
        app.state.runtime_settings = settings
        app.state.startup_checks_completed = False

        if run_startup_checks:
            get_chat_service()

        langfuse_client = initialize_observability(settings) if enable_observability else None
        app.state.langfuse_client = langfuse_client
        app.state.startup_checks_completed = True

        try:
            yield
        finally:
            client: Any = getattr(app.state, "langfuse_client", None)
            if client is not None:
                client.flush()

    return lifespan


def create_app(*, enable_observability: bool = True, run_startup_checks: bool = True) -> FastAPI:
    settings = get_runtime_settings()
    app = FastAPI(
        title="Customer Bot API",
        version="0.1.0",
        lifespan=create_lifespan(
            enable_observability=enable_observability,
            run_startup_checks=run_startup_checks,
        ),
    )
    app.state.limiter = limiter

    async def handle_api_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, ApiError)
        return await api_error_handler(request, exc)

    async def handle_validation_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RequestValidationError)
        return await validation_exception_handler(request, exc)

    async def handle_rate_limit_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RateLimitExceeded)
        return await rate_limit_exception_handler(request, exc)

    async def handle_http_error(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, StarletteHTTPException)
        return await http_exception_handler(request, exc)

    async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
        return await unhandled_exception_handler(request, exc)

    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_allow_origins,
        allow_credentials=settings.api_cors_allow_credentials,
        allow_methods=settings.api_cors_allow_methods,
        allow_headers=settings.api_cors_allow_headers,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.api_trusted_hosts)
    app.include_router(router)
    app.middleware("http")(request_context_middleware)
    return app


def main() -> None:
    clear_dependency_caches()
    settings = get_runtime_settings()
    uvicorn.run(
        create_app(enable_observability=True),
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
