from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import LLM
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from customer_bot.config import Settings
from customer_bot.llm_providers.common import compact_kwargs, require_api_key


def build_openai_llm(settings: Settings) -> LLM:
    api_key = require_api_key(
        provider="openai",
        env_var="OPENAI_API_KEY",
        value=settings.openai_api_key,
    )
    optional_kwargs = compact_kwargs(
        {
            "temperature": settings.openai_llm_temperature,
            "max_tokens": settings.openai_llm_max_tokens,
            "max_retries": settings.openai_llm_max_retries,
            "timeout": settings.openai_llm_timeout_seconds,
            "api_base": settings.openai_llm_api_base,
            "api_version": settings.openai_llm_api_version,
            "strict": settings.openai_llm_strict,
            "reasoning_effort": settings.openai_llm_reasoning_effort,
        }
    )
    return OpenAI(
        model=settings.openai_llm_model,
        api_key=api_key,
        **optional_kwargs,
    )


def build_openai_embedding(settings: Settings) -> BaseEmbedding:
    api_key = require_api_key(
        provider="openai",
        env_var="OPENAI_API_KEY",
        value=settings.openai_api_key,
    )
    optional_kwargs = compact_kwargs(
        {
            "mode": settings.openai_embedding_mode,
            "embed_batch_size": settings.openai_embedding_batch_size,
            "dimensions": settings.openai_embedding_dimensions,
            "max_retries": settings.openai_embedding_max_retries,
            "timeout": settings.openai_embedding_timeout_seconds,
            "api_base": settings.openai_embedding_api_base,
            "api_version": settings.openai_embedding_api_version,
            "num_workers": settings.openai_embedding_num_workers,
        }
    )
    return OpenAIEmbedding(
        model=settings.openai_embedding_model,
        api_key=api_key,
        **optional_kwargs,
    )
