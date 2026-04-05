from __future__ import annotations

import pytest

from customer_bot.llama import create_embedding_model, create_llm


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
