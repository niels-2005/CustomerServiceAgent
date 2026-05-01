from __future__ import annotations

import pytest

import customer_bot.llm_providers.common as common_provider
import customer_bot.llm_providers.ollama as ollama_provider
import customer_bot.llm_providers.openai as openai_provider


class _CaptureInit:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.mark.unit
def test_openai_llm_forwards_only_explicit_optional_kwargs(monkeypatch, settings_factory) -> None:
    monkeypatch.setattr(openai_provider, "OpenAI", _CaptureInit)
    settings = settings_factory(
        llm_provider="openai",
        openai_llm_context_window=400000,
        openai_llm_temperature=0.2,
        openai_llm_max_completion_tokens=500,
        openai_llm_strict=True,
        openai_llm_reasoning_effort="low",
    )

    llm = openai_provider.build_openai_llm(settings)

    assert llm.kwargs["model"] == "gpt-4o-mini"
    assert llm.kwargs["api_key"] == "sk-test-openai"
    assert llm.kwargs["context_window"] == 400000
    assert llm.kwargs["temperature"] == 0.2
    assert llm.kwargs["additional_kwargs"] == {"max_completion_tokens": 500}
    assert llm.kwargs["strict"] is True
    assert llm.kwargs["reasoning_effort"] == "low"
    assert "max_tokens" not in llm.kwargs
    assert "timeout" not in llm.kwargs


@pytest.mark.unit
def test_ollama_builders_filter_unset_optional_kwargs(monkeypatch, settings_factory) -> None:
    monkeypatch.setattr(ollama_provider, "Ollama", _CaptureInit)
    monkeypatch.setattr(ollama_provider, "OllamaEmbedding", _CaptureInit)
    settings = settings_factory(
        llm_provider="ollama",
        embedding_provider="ollama",
        ollama_temperature=0.1,
        ollama_keep_alive="15m",
        ollama_embedding_batch_size=16,
        ollama_embedding_num_ctx=2048,
    )

    llm = ollama_provider.build_ollama_llm(settings)
    embedding = ollama_provider.build_ollama_embedding(settings)

    assert llm.kwargs["temperature"] == 0.1
    assert llm.kwargs["keep_alive"] == "15m"
    assert "base_url" not in llm.kwargs
    assert "request_timeout" not in llm.kwargs
    assert "json_mode" not in llm.kwargs
    assert "thinking" not in llm.kwargs
    assert "context_window" not in llm.kwargs

    assert embedding.kwargs["embed_batch_size"] == 16
    assert embedding.kwargs["ollama_additional_kwargs"] == {"num_ctx": 2048}
    assert "base_url" not in embedding.kwargs
    assert "client_kwargs" not in embedding.kwargs
    assert "query_instruction" not in embedding.kwargs


@pytest.mark.unit
def test_ollama_builders_forward_explicit_connection_overrides(
    monkeypatch, settings_factory
) -> None:
    monkeypatch.setattr(ollama_provider, "Ollama", _CaptureInit)
    monkeypatch.setattr(ollama_provider, "OllamaEmbedding", _CaptureInit)
    settings = settings_factory(
        llm_provider="ollama",
        embedding_provider="ollama",
        ollama_base_url="http://ollama.internal:11434",
        ollama_request_timeout_seconds=120.0,
        ollama_thinking="high",
        ollama_context_window=16384,
    )

    llm = ollama_provider.build_ollama_llm(settings)
    embedding = ollama_provider.build_ollama_embedding(settings)

    assert llm.kwargs["base_url"] == "http://ollama.internal:11434"
    assert llm.kwargs["request_timeout"] == 120.0
    assert llm.kwargs["thinking"] == "high"
    assert llm.kwargs["context_window"] == 16384

    assert embedding.kwargs["base_url"] == "http://ollama.internal:11434"
    assert embedding.kwargs["client_kwargs"] == {"timeout": 120.0}


@pytest.mark.unit
def test_require_api_key_rejects_blank_values() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        common_provider.require_api_key(
            provider="openai",
            env_var="OPENAI_API_KEY",
            value="   ",
        )


@pytest.mark.unit
def test_compact_kwargs_removes_empty_values() -> None:
    compacted = common_provider.compact_kwargs(
        {
            "temperature": 0,
            "timeout": None,
            "api_base": "",
            "headers": {},
        }
    )

    assert compacted == {"temperature": 0}


@pytest.mark.unit
def test_openai_embedding_requires_api_key(monkeypatch, settings_factory) -> None:
    monkeypatch.setattr(openai_provider, "OpenAIEmbedding", _CaptureInit)
    settings = settings_factory(embedding_provider="openai", OPENAI_API_KEY="")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        openai_provider.build_openai_embedding(settings)
