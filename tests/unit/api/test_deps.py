from __future__ import annotations

from customer_bot.api.deps import (
    clear_dependency_caches,
    get_agent_service,
    get_chat_service,
    get_guardrail_service,
    get_memory_backend,
    get_product_retriever_service,
    get_retriever_service,
    get_runtime_settings,
)


def test_dependency_factories_cache_instances(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=False)
    monkeypatch.setattr("customer_bot.api.deps.get_settings", lambda: settings)
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
    monkeypatch.setattr("customer_bot.api.deps.get_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())

    clear_dependency_caches()
    first = get_chat_service()
    clear_dependency_caches()
    second = get_chat_service()

    assert first is not second


def test_chat_service_omits_guardrails_when_disabled(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=False)
    monkeypatch.setattr("customer_bot.api.deps.get_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())

    clear_dependency_caches()
    service = get_chat_service()

    assert service._guardrail_service is None


def test_chat_service_wires_guardrails_when_enabled(monkeypatch, settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=True)
    monkeypatch.setattr("customer_bot.api.deps.get_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda _settings: object())
    monkeypatch.setattr("customer_bot.api.deps.create_guardrail_llm", lambda _settings: object())

    clear_dependency_caches()
    service = get_chat_service()
    guardrail_service = get_guardrail_service()

    assert service._guardrail_service is guardrail_service
