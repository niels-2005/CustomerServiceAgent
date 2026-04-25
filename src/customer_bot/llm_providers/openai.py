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
            "temperature": settings.llm.openai.temperature,
            "max_retries": settings.llm.openai.max_retries,
            "timeout": settings.llm.openai.timeout_seconds,
            "api_base": settings.llm.openai.api_base,
            "api_version": settings.llm.openai.api_version,
            "strict": settings.llm.openai.strict,
            "reasoning_effort": settings.llm.openai.reasoning_effort,
        }
    )
    additional_kwargs = compact_kwargs(
        {
            "max_completion_tokens": settings.llm.openai.max_completion_tokens,
        }
    )
    return OpenAI(
        model=settings.llm.openai.model,
        api_key=api_key,
        additional_kwargs=additional_kwargs,
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
            "mode": settings.embedding.openai.mode,
            "embed_batch_size": settings.embedding.openai.batch_size,
            "dimensions": settings.embedding.openai.dimensions,
            "max_retries": settings.embedding.openai.max_retries,
            "timeout": settings.embedding.openai.timeout_seconds,
            "api_base": settings.embedding.openai.api_base,
            "api_version": settings.embedding.openai.api_version,
            "num_workers": settings.embedding.openai.num_workers,
        }
    )
    return OpenAIEmbedding(
        model=settings.embedding.openai.model,
        api_key=api_key,
        **optional_kwargs,
    )
