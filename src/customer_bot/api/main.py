from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI

from customer_bot.api.deps import clear_dependency_caches, get_runtime_settings
from customer_bot.api.routes import router
from customer_bot.observability import initialize_observability


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_runtime_settings()
    langfuse_client = initialize_observability(settings)
    app.state.langfuse_client = langfuse_client

    try:
        yield
    finally:
        client: Any = getattr(app.state, "langfuse_client", None)
        if client is not None:
            client.flush()


def create_app(*, enable_observability: bool = True) -> FastAPI:
    app = FastAPI(
        title="Customer Bot API",
        version="0.1.0",
        lifespan=lifespan if enable_observability else None,
    )
    app.include_router(router)
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
