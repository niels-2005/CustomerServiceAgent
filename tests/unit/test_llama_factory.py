from __future__ import annotations

import pytest

import customer_bot.model_factory as model_factory
from customer_bot.model_factory import create_embedding_model, create_guardrail_llm, create_llm


@pytest.mark.unit
def test_create_llm_applies_ollama_runtime_parameters(settings_factory) -> None:
    settings = settings_factory(
        ollama_chat_model="qwen3:8b",
        ollama_request_timeout_seconds=360.0,
        ollama_thinking=True,
        ollama_context_window=8000,
        ollama_keep_alive="10m",
    )

    llm = create_llm(settings)

    assert llm.model == "qwen3:8b"
    assert llm.request_timeout == 360.0
    assert llm.thinking is True
    assert llm.context_window == 8000
    assert llm.keep_alive == "10m"


@pytest.mark.unit
def test_create_embedding_model_uses_optional_num_ctx(settings_factory) -> None:
    settings = settings_factory(ollama_embedding_num_ctx=4096)

    embedding = create_embedding_model(settings)

    assert embedding.ollama_additional_kwargs == {"num_ctx": 4096}


@pytest.mark.unit
def test_create_embedding_model_without_num_ctx(settings_factory) -> None:
    settings = settings_factory(ollama_embedding_num_ctx=None)

    embedding = create_embedding_model(settings)

    assert embedding.ollama_additional_kwargs == {}


@pytest.mark.unit
def test_create_llm_dispatches_provider_builder(monkeypatch, settings_factory) -> None:
    marker = object()

    def _fake_builder(_settings):
        return marker

    monkeypatch.setitem(model_factory._LLM_BUILDERS, "openai", _fake_builder)
    settings = settings_factory(llm_provider="openai")

    assert create_llm(settings) is marker


@pytest.mark.unit
def test_create_embedding_dispatches_provider_builder(monkeypatch, settings_factory) -> None:
    marker = object()

    def _fake_builder(_settings):
        return marker

    monkeypatch.setitem(model_factory._EMBEDDING_BUILDERS, "openai", _fake_builder)
    settings = settings_factory(embedding_provider="openai")

    assert create_embedding_model(settings) is marker


@pytest.mark.unit
def test_create_llm_requires_provider_key(settings_factory) -> None:
    settings = settings_factory(llm_provider="openai", OPENAI_API_KEY="")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_llm(settings)


@pytest.mark.unit
def test_create_embedding_requires_provider_key(settings_factory) -> None:
    settings = settings_factory(embedding_provider="openai", OPENAI_API_KEY="")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_embedding_model(settings)


@pytest.mark.unit
def test_create_llm_errors_when_provider_registry_entry_missing(
    monkeypatch, settings_factory
) -> None:
    monkeypatch.delitem(model_factory._LLM_BUILDERS, "openai")
    settings = settings_factory(llm_provider="openai")

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm(settings)


@pytest.mark.unit
def test_create_embedding_errors_when_provider_registry_entry_missing(
    monkeypatch, settings_factory
) -> None:
    monkeypatch.delitem(model_factory._EMBEDDING_BUILDERS, "openai")
    settings = settings_factory(embedding_provider="openai")

    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        create_embedding_model(settings)


@pytest.mark.unit
def test_create_guardrail_llm_requires_supported_provider(settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=True, guardrail_provider="openai")

    client = create_guardrail_llm(settings)

    assert client is not None
    assert client.model == settings.openai_guardrail_model


@pytest.mark.unit
def test_create_guardrail_llm_requires_api_key(settings_factory) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        guardrail_provider="openai",
        OPENAI_API_KEY="",
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_guardrail_llm(settings)
