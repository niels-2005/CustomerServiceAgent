from __future__ import annotations

from llama_index.core.llms.llm import LLM
from llama_index.llms.openrouter import OpenRouter

from customer_bot.config import Settings
from customer_bot.llm_providers.common import compact_kwargs, require_api_key


def build_openrouter_llm(settings: Settings) -> LLM:
    api_key = require_api_key(
        provider="openrouter",
        env_var="OPENROUTER_API_KEY",
        value=settings.openrouter_api_key,
    )
    optional_kwargs = compact_kwargs(
        {
            "temperature": settings.openrouter_temperature,
            "max_tokens": settings.openrouter_max_tokens,
            "context_window": settings.openrouter_context_window,
            "max_retries": settings.openrouter_max_retries,
            "api_base": settings.openrouter_api_base,
            "allow_fallbacks": settings.openrouter_allow_fallbacks,
        }
    )
    return OpenRouter(
        model=settings.openrouter_llm_model,
        api_key=api_key,
        **optional_kwargs,
    )
