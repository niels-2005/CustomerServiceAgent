from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from customer_bot.api.main import create_app


def test_lifespan_sets_runtime_state_and_flushes_langfuse_client(
    monkeypatch, settings_factory
) -> None:
    settings = settings_factory()
    flushed: list[str] = []
    redis_calls: list[str] = []

    class FakeLangfuseClient:
        def flush(self) -> None:
            flushed.append("flush")

    class FakeRedisClient:
        async def ping(self) -> bool:
            redis_calls.append("ping")
            return True

        async def aclose(self) -> None:
            redis_calls.append("close")

    async def validate_chat_memory_storage() -> None:
        client = FakeRedisClient()
        await client.ping()

    async def close_memory_redis_client() -> None:
        client = FakeRedisClient()
        await client.aclose()

    monkeypatch.setattr("customer_bot.api.main.get_runtime_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.main.get_chat_service", lambda: object())
    monkeypatch.setattr("customer_bot.api.main.get_memory_redis_client", lambda: FakeRedisClient())
    monkeypatch.setattr(
        "customer_bot.api.main.validate_chat_memory_storage",
        validate_chat_memory_storage,
    )
    monkeypatch.setattr(
        "customer_bot.api.main.close_memory_redis_client",
        close_memory_redis_client,
    )
    monkeypatch.setattr(
        "customer_bot.api.main.initialize_observability",
        lambda _settings: FakeLangfuseClient(),
    )

    app = create_app(enable_observability=True, run_startup_checks=True)

    with TestClient(app):
        assert app.state.runtime_settings is settings
        assert app.state.startup_checks_completed is True
        assert app.state.langfuse_client is not None

    assert flushed == ["flush"]
    assert redis_calls == ["ping", "close"]


def test_lifespan_skips_startup_chat_stack_when_disabled(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    startup_calls: list[str] = []
    redis_calls: list[str] = []

    monkeypatch.setattr("customer_bot.api.main.get_runtime_settings", lambda: settings)
    monkeypatch.setattr(
        "customer_bot.api.main.get_chat_service",
        lambda: startup_calls.append("chat_service"),
    )

    async def validate_chat_memory_storage() -> None:
        redis_calls.append("ping")

    async def close_memory_redis_client() -> None:
        redis_calls.append("close")

    monkeypatch.setattr("customer_bot.api.main.get_memory_redis_client", lambda: object())
    monkeypatch.setattr(
        "customer_bot.api.main.validate_chat_memory_storage", validate_chat_memory_storage
    )
    monkeypatch.setattr(
        "customer_bot.api.main.close_memory_redis_client", close_memory_redis_client
    )

    app = create_app(enable_observability=False, run_startup_checks=False)

    with TestClient(app):
        assert app.state.langfuse_client is None
        assert app.state.startup_checks_completed is True

    assert startup_calls == []
    assert redis_calls == ["close"]


def test_lifespan_fails_fast_when_chat_memory_redis_is_unavailable(
    monkeypatch, settings_factory
) -> None:
    settings = settings_factory()

    async def validate_chat_memory_storage() -> None:
        raise RuntimeError("Chat memory Redis backend is unavailable")

    async def close_memory_redis_client() -> None:
        return None

    monkeypatch.setattr("customer_bot.api.main.get_runtime_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.main.get_memory_redis_client", lambda: object())
    monkeypatch.setattr(
        "customer_bot.api.main.validate_chat_memory_storage",
        validate_chat_memory_storage,
    )
    monkeypatch.setattr(
        "customer_bot.api.main.close_memory_redis_client", close_memory_redis_client
    )

    app = create_app(enable_observability=False, run_startup_checks=True)

    with pytest.raises(RuntimeError, match="Chat memory Redis backend is unavailable"):
        with TestClient(app):
            pass
