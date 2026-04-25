"""Ollama-backed LLM and embedding builders."""

from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import LLM
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from customer_bot.config import Settings
from customer_bot.llm_providers.common import compact_kwargs


def build_ollama_llm(settings: Settings) -> LLM:
    """Build the configured Ollama chat model."""
    optional_kwargs = compact_kwargs(
        {
            "base_url": settings.llm.ollama.base_url,
            "temperature": settings.llm.ollama.temperature,
            "request_timeout": settings.llm.ollama.request_timeout_seconds,
            "prompt_key": settings.llm.ollama.prompt_key,
            "json_mode": settings.llm.ollama.json_mode,
            "keep_alive": settings.llm.ollama.keep_alive,
            "thinking": settings.llm.ollama.thinking,
            "context_window": settings.llm.ollama.context_window,
        }
    )
    return Ollama(
        model=settings.llm.ollama.chat_model,
        **optional_kwargs,
    )


def build_ollama_embedding(settings: Settings) -> BaseEmbedding:
    """Build the configured Ollama embedding model."""
    additional_kwargs = compact_kwargs({"num_ctx": settings.embedding.ollama.num_ctx})
    # Embeddings reuse the LLM timeout/base URL wiring so one runtime config
    # controls both Ollama clients consistently.
    client_kwargs = compact_kwargs({"timeout": settings.llm.ollama.request_timeout_seconds})
    optional_kwargs = compact_kwargs(
        {
            "base_url": settings.llm.ollama.base_url,
            "embed_batch_size": settings.embedding.ollama.batch_size,
            "query_instruction": settings.embedding.ollama.query_instruction,
            "text_instruction": settings.embedding.ollama.text_instruction,
            "keep_alive": settings.embedding.ollama.keep_alive,
            "client_kwargs": client_kwargs,
            "ollama_additional_kwargs": additional_kwargs,
        }
    )
    return OllamaEmbedding(
        model_name=settings.embedding.ollama.model,
        **optional_kwargs,
    )
