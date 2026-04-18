from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import LLM
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

from customer_bot.config import Settings
from customer_bot.llm_providers.common import compact_kwargs, require_api_key


def build_gemini_llm(settings: Settings) -> LLM:
    api_key = require_api_key(
        provider="gemini",
        env_var="GOOGLE_API_KEY",
        value=settings.google_api_key,
    )
    optional_kwargs = compact_kwargs(
        {
            "temperature": settings.gemini_llm_temperature,
            "max_tokens": settings.gemini_llm_max_tokens,
            "context_window": settings.gemini_llm_context_window,
            "max_retries": settings.gemini_llm_max_retries,
            "cached_content": settings.gemini_llm_cached_content,
            "file_mode": settings.gemini_llm_file_mode,
        }
    )
    return GoogleGenAI(
        model=settings.gemini_llm_model,
        api_key=api_key,
        **optional_kwargs,
    )


def build_gemini_embedding(settings: Settings) -> BaseEmbedding:
    api_key = require_api_key(
        provider="gemini",
        env_var="GOOGLE_API_KEY",
        value=settings.google_api_key,
    )
    optional_kwargs = compact_kwargs(
        {
            "embed_batch_size": settings.gemini_embedding_batch_size,
            "retries": settings.gemini_embedding_retries,
            "timeout": settings.gemini_embedding_timeout_seconds,
            "retry_min_seconds": settings.gemini_embedding_retry_min_seconds,
            "retry_max_seconds": settings.gemini_embedding_retry_max_seconds,
            "retry_exponential_base": settings.gemini_embedding_retry_exponential_base,
        }
    )
    return GoogleGenAIEmbedding(
        model_name=settings.gemini_embedding_model,
        api_key=api_key,
        **optional_kwargs,
    )
