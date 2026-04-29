from __future__ import annotations

import pytest

from customer_bot.api.deps import (
    clear_dependency_caches,
    close_memory_redis_client,
    get_agent_service,
    get_chat_service,
    get_guardrail_service,
    get_memory_backend,
    get_memory_redis_client,
    get_product_retriever_service,
    get_retriever_service,
    get_runtime_settings,
    validate_chat_memory_storage,
)
from customer_bot.memory.backend import RedisSessionMemoryBackend


class FakeRedisClient:
    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self.ping_error = ping_error
        self.closed = False

    async def ping(self) -> bool:
        if self.ping_error is not None:
            raise self.ping_error
        return True

    async def aclose(self) -> None:
        self.closed = True

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        del key, start, end
        return []

    async def eval(self, script: str, numkeys: int, key: str, *args: str) -> int:
        del script, numkeys, key, args
        return 1


def test_dependency_factories_cache_instances(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=False)
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())
    monkeypatch.setattr("customer_bot.api.deps.create_guardrail_llm", lambda _settings: object())

    clear_dependency_caches()

    assert get_runtime_settings() is settings
    assert get_retriever_service() is get_retriever_service()
    assert get_product_retriever_service() is get_product_retriever_service()
    assert get_agent_service() is get_agent_service()
    assert get_memory_backend() is get_memory_backend()
    assert get_chat_service() is get_chat_service()


def test_clear_dependency_caches_rebuilds_instances(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=False)
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())

    clear_dependency_caches()
    first = get_chat_service()
    clear_dependency_caches()
    second = get_chat_service()

    assert first is not second


def test_chat_service_omits_guardrails_when_disabled(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=False)
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())

    clear_dependency_caches()
    service = get_chat_service()

    assert service._guardrail_service is None


def test_chat_service_wires_guardrails_when_enabled(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=True)
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())
    monkeypatch.setattr("customer_bot.api.deps.create_guardrail_llm", lambda _settings: object())

    clear_dependency_caches()
    service = get_chat_service()
    guardrail_service = get_guardrail_service()

    assert service._guardrail_service is guardrail_service


def test_get_memory_backend_uses_redis_backend(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    fake_client = FakeRedisClient()
    monkeypatch.setattr(
        "customer_bot.api.deps.Redis.from_url",
        lambda url, decode_responses: fake_client,
    )
    clear_dependency_caches()

    backend = get_memory_backend()

    assert isinstance(backend, RedisSessionMemoryBackend)
    assert backend._key_prefix == settings.memory.redis.key_prefix
    assert get_memory_redis_client() is fake_client


def test_validate_chat_memory_storage_pings_cached_redis_client(
    monkeypatch, settings_factory
) -> None:
    import asyncio

    settings = settings_factory()
    fake_client = FakeRedisClient()
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr(
        "customer_bot.api.deps.Redis.from_url",
        lambda url, decode_responses: fake_client,
    )
    clear_dependency_caches()

    asyncio.run(validate_chat_memory_storage())

    assert get_memory_redis_client() is fake_client


def test_validate_chat_memory_storage_raises_when_ping_fails(monkeypatch, settings_factory) -> None:
    import asyncio

    settings = settings_factory()
    fake_client = FakeRedisClient(ping_error=RuntimeError("boom"))
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr(
        "customer_bot.api.deps.Redis.from_url",
        lambda url, decode_responses: fake_client,
    )
    clear_dependency_caches()

    with pytest.raises(RuntimeError, match="Chat memory Redis backend is unavailable"):
        asyncio.run(validate_chat_memory_storage())


def test_close_memory_redis_client_closes_cached_client(monkeypatch, settings_factory) -> None:
    import asyncio

    settings = settings_factory()
    fake_client = FakeRedisClient()
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr(
        "customer_bot.api.deps.Redis.from_url",
        lambda url, decode_responses: fake_client,
    )
    clear_dependency_caches()

    assert get_memory_redis_client() is fake_client

    asyncio.run(close_memory_redis_client())

    assert fake_client.closed is True
