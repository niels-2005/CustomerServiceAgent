from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from customer_bot.config import Settings


def create_llm(settings: Settings) -> Ollama:
    return Ollama(
        model=settings.ollama_chat_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout_seconds,
        is_function_calling_model=True,
    )


def create_embedding_model(settings: Settings) -> BaseEmbedding:
    return OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
        ollama_additional_kwargs={"num_ctx": 2048},
        client_kwargs={"timeout": settings.ollama_request_timeout_seconds},
    )
