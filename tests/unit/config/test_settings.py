from __future__ import annotations

from pathlib import Path

import pytest

from customer_bot.api.deps import clear_dependency_caches
from customer_bot.config import Settings, get_settings


def test_settings_load_yaml_defaults(monkeypatch) -> None:
    monkeypatch.delenv("SELECTORS__LLM", raising=False)
    monkeypatch.delenv("SELECTORS__EMBEDDING", raising=False)
    monkeypatch.delenv("API__PORT", raising=False)
    monkeypatch.delenv("RETRIEVAL__FAQ__TOP_K", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://:rate@127.0.0.1:6379/1")
    monkeypatch.setenv("CHAT_MEMORY_REDIS_URL", "redis://:secret@127.0.0.1:6379/2")

    settings = Settings(_env_file=None)

    assert settings.api.host == "0.0.0.0"
    assert settings.api.port == 8000
    assert settings.selectors.llm == "openai"
    assert settings.selectors.embedding == "openai"
    assert settings.retrieval.faq.top_k == 1
    assert settings.retrieval.products.top_k == 1
    assert settings.ingestion.products.corpus_csv_path == Path("dataset/products.csv")
    assert settings.storage.products.collection_name == "customer_bot_products"
    assert settings.retrieval.products.similarity_cutoff == 0.2
    assert settings.guardrails.input.pii.presidio_config_path == Path(
        "src/customer_bot/config/defaults/presidio_config.yaml"
    )
    assert "konto" in settings.guardrails.input.topic_relevance.allowed_domain_hints
    assert "alle frauen" in settings.guardrails.output.bias.bias_terms
    assert settings.openai_api_key == ""
    assert settings.api.rate_limit.storage_uri == "redis://:rate@127.0.0.1:6379/1"
    assert settings.memory.redis.redis_url == "redis://:secret@127.0.0.1:6379/2"


def test_env_overrides_yaml_defaults(monkeypatch) -> None:
    monkeypatch.setenv("API__PORT", "9100")
    monkeypatch.setenv("RETRIEVAL__FAQ__TOP_K", "7")
    monkeypatch.setenv("LLM__OLLAMA__BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("INGESTION__PRODUCTS__CORPUS_CSV_PATH", "dataset/custom-products.csv")
    monkeypatch.setenv("RETRIEVAL__PRODUCTS__SIMILARITY_CUTOFF", "0.82")
    monkeypatch.setenv("CHAT_MEMORY_REDIS_URL", "redis://:chat@127.0.0.1:6379/2")
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://:rate@127.0.0.1:6379/1")

    settings = Settings(_env_file=None)

    assert settings.api.port == 9100
    assert settings.retrieval.faq.top_k == 7
    assert settings.llm.ollama.base_url == "http://127.0.0.1:11434"
    assert settings.ingestion.products.corpus_csv_path == Path("dataset/custom-products.csv")
    assert settings.retrieval.products.similarity_cutoff == 0.82
    assert settings.memory.redis.redis_url == "redis://:chat@127.0.0.1:6379/2"
    assert settings.api.rate_limit.storage_uri == "redis://:rate@127.0.0.1:6379/1"


def test_settings_apply_langfuse_host_env_compatibility_override(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://:rate@127.0.0.1:6379/1")
    monkeypatch.setenv("CHAT_MEMORY_REDIS_URL", "redis://:secret@127.0.0.1:6379/2")
    monkeypatch.setenv("LANGFUSE_HOST", "https://langfuse.override")

    settings = Settings(_env_file=None)

    assert settings.langfuse.host == "https://langfuse.override"


def test_get_settings_is_cached_until_cleared(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://:rate@127.0.0.1:6379/1")
    monkeypatch.setenv("CHAT_MEMORY_REDIS_URL", "redis://:secret@127.0.0.1:6379/2")
    monkeypatch.setenv("API__PORT", "8300")
    clear_dependency_caches()

    first = get_settings()
    monkeypatch.setenv("API__PORT", "8400")
    second = get_settings()
    clear_dependency_caches()
    third = get_settings()

    assert first is second
    assert first.api.port == 8300
    assert third.api.port == 8400


def test_settings_require_chat_memory_redis_url(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://:rate@127.0.0.1:6379/1")
    monkeypatch.delenv("CHAT_MEMORY_REDIS_URL", raising=False)

    with pytest.raises(ValueError, match="CHAT_MEMORY_REDIS_URL"):
        Settings(_env_file=None)


def test_settings_require_rate_limit_redis_url(monkeypatch) -> None:
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.setenv("CHAT_MEMORY_REDIS_URL", "redis://:chat@127.0.0.1:6379/2")

    with pytest.raises(ValueError, match="RATE_LIMIT_REDIS_URL"):
        Settings(_env_file=None)
