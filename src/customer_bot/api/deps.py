"""Dependency wiring for the FastAPI layer.

These factories centralize singleton-style runtime objects behind cached
functions so routes can stay declarative while tests can reset state explicitly.
"""

from __future__ import annotations

from functools import lru_cache

from customer_bot.agent.service import AgentService
from customer_bot.chat.service import ChatService
from customer_bot.config import Settings, get_settings
from customer_bot.guardrails.service import GuardrailService
from customer_bot.memory.backend import InMemorySessionMemoryBackend
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
def get_memory_backend() -> InMemorySessionMemoryBackend:
    """Return the cached in-memory session store."""
    settings = get_settings()
    return InMemorySessionMemoryBackend(max_turns=settings.memory.max_turns)


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
    get_memory_backend.cache_clear()
    get_chat_service.cache_clear()


def get_runtime_settings() -> Settings:
    """Expose runtime settings through a dedicated dependency helper."""
    return get_settings()
