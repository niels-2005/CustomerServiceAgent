"""Factory functions for LLM, embedding, and guardrail model clients.

This module keeps provider selection explicit and centralized so startup wiring
fails fast when configuration is incomplete or unsupported.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import LLM
from openai import AsyncOpenAI

from customer_bot.config import EmbeddingProvider, LlmProvider, Settings
from customer_bot.llm_providers import (
    build_ollama_embedding,
    build_ollama_llm,
    build_openai_embedding,
    build_openai_llm,
)
from customer_bot.llm_providers.common import compact_kwargs, require_api_key


class LlmBuilder(Protocol):
    """Callable signature for provider-specific LLM builders."""

    def __call__(self, settings: Settings) -> LLM: ...


class EmbeddingBuilder(Protocol):
    """Callable signature for provider-specific embedding builders."""

    def __call__(self, settings: Settings) -> BaseEmbedding: ...


_LLM_BUILDERS: dict[LlmProvider, LlmBuilder] = {
    "ollama": build_ollama_llm,
    "openai": build_openai_llm,
}

_EMBEDDING_BUILDERS: dict[EmbeddingProvider, EmbeddingBuilder] = {
    "ollama": build_ollama_embedding,
    "openai": build_openai_embedding,
}


def create_llm(settings: Settings) -> LLM:
    """Create the configured chat model for runtime agent execution."""
    builder = _LLM_BUILDERS.get(settings.selectors.llm)
    if builder is None:
        raise ValueError(f"Unsupported LLM provider: {settings.selectors.llm}")
    return builder(settings)


def create_embedding_model(settings: Settings) -> BaseEmbedding:
    """Create the configured embedding model for ingestion and retrieval."""
    builder = _EMBEDDING_BUILDERS.get(settings.selectors.embedding)
    if builder is None:
        raise ValueError(f"Unsupported embedding provider: {settings.selectors.embedding}")
    return builder(settings)


@dataclass(slots=True)
class GuardrailOpenAIClient:
    """Small wrapper around AsyncOpenAI for structured guardrail calls."""

    client: AsyncOpenAI
    model: str
    temperature: float | None = None
    max_completion_tokens: int | None = None
    reasoning_effort: str | None = None

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, object],
    ) -> str:
        """Request JSON output that must satisfy the provided schema."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{user_prompt}\n\n"
                        "Return valid JSON only. The JSON must satisfy this schema:\n"
                        f"{json.dumps(output_schema, ensure_ascii=True)}"
                    ),
                },
            ],
            **compact_kwargs(
                {
                    "temperature": self.temperature,
                    "max_completion_tokens": self.max_completion_tokens,
                    "reasoning_effort": self.reasoning_effort,
                    "response_format": {"type": "json_object"},
                }
            ),
        )
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.text
                for item in content
                if hasattr(item, "text") and isinstance(item.text, str)
            )
        raise RuntimeError("Guardrail model returned an empty response.")


def create_guardrail_llm(settings: Settings) -> GuardrailOpenAIClient | None:
    """Create the guardrail LLM client when guardrails are enabled."""
    if not settings.guardrails.global_.enabled:
        return None
    # Guardrail prompting is currently implemented only for OpenAI-compatible
    # structured JSON responses.
    if settings.selectors.guardrail != "openai":
        raise ValueError(f"Unsupported guardrail provider: {settings.selectors.guardrail}")

    api_key = require_api_key(
        provider="openai-guardrail",
        env_var="OPENAI_API_KEY",
        value=settings.openai_api_key,
    )
    client = AsyncOpenAI(
        **compact_kwargs(
            {
                "api_key": api_key,
                "base_url": settings.guardrail.openai.api_base,
                "timeout": settings.guardrail.openai.timeout_seconds,
                "max_retries": settings.guardrail.openai.max_retries,
            }
        )
    )
    return GuardrailOpenAIClient(
        client=client,
        model=settings.guardrail.openai.model,
        temperature=settings.guardrail.openai.temperature,
        max_completion_tokens=settings.guardrail.openai.max_completion_tokens,
        reasoning_effort=settings.guardrail.openai.reasoning_effort,
    )
