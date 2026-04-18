from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from customer_bot.config import Settings


def create_llm(settings: Settings) -> Ollama:
    if settings.ollama_keep_alive in (None, ""):
        return Ollama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            request_timeout=settings.ollama_request_timeout_seconds,
            thinking=settings.ollama_thinking,
            context_window=settings.ollama_context_window,
        )

    return Ollama(
        model=settings.ollama_chat_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout_seconds,
        thinking=settings.ollama_thinking,
        context_window=settings.ollama_context_window,
        keep_alive=settings.ollama_keep_alive,
    )


def create_embedding_model(settings: Settings) -> BaseEmbedding:
    additional_kwargs = None
    if settings.ollama_embedding_num_ctx is not None:
        additional_kwargs = {"num_ctx": settings.ollama_embedding_num_ctx}

    return OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
        ollama_additional_kwargs=additional_kwargs,
        client_kwargs={"timeout": settings.ollama_request_timeout_seconds},
    )
