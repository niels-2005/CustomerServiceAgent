from __future__ import annotations

from typing import Protocol

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import LLM

from customer_bot.config import EmbeddingProvider, LlmProvider, Settings
from customer_bot.llm_providers import (
    build_gemini_embedding,
    build_gemini_llm,
    build_ollama_embedding,
    build_ollama_llm,
    build_openai_embedding,
    build_openai_llm,
    build_openrouter_llm,
)


class LlmBuilder(Protocol):
    def __call__(self, settings: Settings) -> LLM: ...


class EmbeddingBuilder(Protocol):
    def __call__(self, settings: Settings) -> BaseEmbedding: ...


_LLM_BUILDERS: dict[LlmProvider, LlmBuilder] = {
    "ollama": build_ollama_llm,
    "openai": build_openai_llm,
    "gemini": build_gemini_llm,
    "openrouter": build_openrouter_llm,
}

_EMBEDDING_BUILDERS: dict[EmbeddingProvider, EmbeddingBuilder] = {
    "ollama": build_ollama_embedding,
    "openai": build_openai_embedding,
    "gemini": build_gemini_embedding,
}


def create_llm(settings: Settings) -> LLM:
    builder = _LLM_BUILDERS.get(settings.llm_provider)
    if builder is None:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    return builder(settings)


def create_embedding_model(settings: Settings) -> BaseEmbedding:
    builder = _EMBEDDING_BUILDERS.get(settings.embedding_provider)
    if builder is None:
        raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
    return builder(settings)
