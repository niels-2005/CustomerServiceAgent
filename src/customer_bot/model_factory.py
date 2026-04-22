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
    def __call__(self, settings: Settings) -> LLM: ...


class EmbeddingBuilder(Protocol):
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
    builder = _LLM_BUILDERS.get(settings.llm_provider)
    if builder is None:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    return builder(settings)


def create_embedding_model(settings: Settings) -> BaseEmbedding:
    builder = _EMBEDDING_BUILDERS.get(settings.embedding_provider)
    if builder is None:
        raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
    return builder(settings)


@dataclass(slots=True)
class GuardrailOpenAIClient:
    client: AsyncOpenAI
    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    reasoning_effort: str | None = None

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, object],
    ) -> str:
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
                    "max_tokens": self.max_tokens,
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
    if not settings.guardrails_enabled:
        return None
    if settings.guardrail_provider != "openai":
        raise ValueError(f"Unsupported guardrail provider: {settings.guardrail_provider}")

    api_key = require_api_key(
        provider="openai-guardrail",
        env_var="OPENAI_API_KEY",
        value=settings.openai_api_key,
    )
    client = AsyncOpenAI(
        **compact_kwargs(
            {
                "api_key": api_key,
                "base_url": settings.openai_guardrail_api_base,
                "timeout": settings.openai_guardrail_timeout_seconds,
                "max_retries": settings.openai_guardrail_max_retries,
            }
        )
    )
    return GuardrailOpenAIClient(
        client=client,
        model=settings.openai_guardrail_model,
        temperature=settings.openai_guardrail_temperature,
        max_tokens=settings.openai_guardrail_max_tokens,
        reasoning_effort=settings.openai_guardrail_reasoning_effort,
    )
