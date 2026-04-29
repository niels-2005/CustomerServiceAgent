"""Dependency wiring for the FastAPI layer.

These factories centralize singleton-style runtime objects behind cached
functions so routes can stay declarative while tests can reset state explicitly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

from redis.asyncio import Redis

from customer_bot.agent.service import AgentService
from customer_bot.chat.service import ChatService
from customer_bot.config import Settings, get_settings
from customer_bot.guardrails.service import GuardrailService
from customer_bot.memory.backend import (
    RedisSessionMemoryBackend,
    SessionMemoryBackend,
    SupportsRedisChatHistory,
)
from customer_bot.model_factory import create_guardrail_llm, create_llm
from customer_bot.retrieval.service import FaqRetrieverService, ProductRetrieverService


@lru_cache(maxsize=1)
def get_retriever_service() -> FaqRetrieverService:
    """Return the cached FAQ retriever service."""
    settings = get_settings()
    return FaqRetrieverService(settings=settings)


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    """Return the cached agent service and its wired dependencies."""
    settings = get_settings()
    llm = create_llm(settings)
    retriever = get_retriever_service()
    product_retriever = get_product_retriever_service()
    return AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=llm,
    )


@lru_cache(maxsize=1)
def get_product_retriever_service() -> ProductRetrieverService:
    """Return the cached product retriever service."""
    settings = get_settings()
    return ProductRetrieverService(settings=settings)


@lru_cache(maxsize=1)
def get_guardrail_service() -> GuardrailService:
    """Return the cached guardrail service."""
    settings = get_settings()
    return GuardrailService(settings=settings, llm_client=create_guardrail_llm(settings))


@lru_cache(maxsize=1)
def get_memory_redis_client() -> Redis:
    """Return the cached Redis client used for chat memory."""
    settings = get_settings()
    redis_settings = settings.memory.redis
    return Redis.from_url(redis_settings.redis_url, decode_responses=True)


@lru_cache(maxsize=1)
def get_memory_backend() -> SessionMemoryBackend:
    """Return the cached Redis-backed session store."""
    settings = get_settings()
    redis_settings = settings.memory.redis
    return RedisSessionMemoryBackend(
        redis_client=cast(SupportsRedisChatHistory, get_memory_redis_client()),
        key_prefix=redis_settings.key_prefix,
        ttl_seconds=redis_settings.ttl_seconds,
        max_turns=settings.memory.max_turns,
    )


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    """Return the cached top-level chat service."""
    settings = get_settings()
    return ChatService(
        memory_backend=get_memory_backend(),
        agent_service=get_agent_service(),
        settings=settings,
        guardrail_service=get_guardrail_service() if settings.guardrails.global_.enabled else None,
    )


def clear_dependency_caches() -> None:
    """Clear cached dependencies so tests and startup can rebuild clean state."""
    get_settings.cache_clear()
    get_retriever_service.cache_clear()
    get_product_retriever_service.cache_clear()
    get_agent_service.cache_clear()
    get_guardrail_service.cache_clear()
    get_memory_redis_client.cache_clear()
    get_memory_backend.cache_clear()
    get_chat_service.cache_clear()


def get_runtime_settings() -> Settings:
    """Expose runtime settings through a dedicated dependency helper."""
    return get_settings()


async def validate_chat_memory_storage() -> None:
    """Fail fast when the configured chat-memory Redis backend is unavailable."""
    try:
        await cast(Any, get_memory_redis_client().ping())
    except Exception as exc:
        settings = get_settings()
        msg = f"Chat memory Redis backend is unavailable: {settings.memory.redis.redis_url}"
        raise RuntimeError(msg) from exc


async def close_memory_redis_client() -> None:
    """Close the cached chat-memory Redis client when the app shuts down."""
    if not get_memory_redis_client.cache_info().currsize:
        return

    client = get_memory_redis_client()
    get_memory_redis_client.cache_clear()
    await client.aclose()
