from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import LLM
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from customer_bot.config import Settings
from customer_bot.llm_providers.common import compact_kwargs


def build_ollama_llm(settings: Settings) -> LLM:
    optional_kwargs = compact_kwargs(
        {
            "temperature": settings.ollama_temperature,
            "prompt_key": settings.ollama_prompt_key,
            "json_mode": settings.ollama_json_mode,
            "keep_alive": settings.ollama_keep_alive,
        }
    )
    return Ollama(
        model=settings.ollama_chat_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout_seconds,
        thinking=settings.ollama_thinking,
        context_window=settings.ollama_context_window,
        **optional_kwargs,
    )


def build_ollama_embedding(settings: Settings) -> BaseEmbedding:
    additional_kwargs = compact_kwargs({"num_ctx": settings.ollama_embedding_num_ctx})
    optional_kwargs = compact_kwargs(
        {
            "embed_batch_size": settings.ollama_embedding_batch_size,
            "query_instruction": settings.ollama_embedding_query_instruction,
            "text_instruction": settings.ollama_embedding_text_instruction,
            "keep_alive": settings.ollama_embedding_keep_alive,
            "ollama_additional_kwargs": additional_kwargs,
        }
    )
    return OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
        client_kwargs={"timeout": settings.ollama_request_timeout_seconds},
        **optional_kwargs,
    )
