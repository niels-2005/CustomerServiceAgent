from __future__ import annotations

from pathlib import Path

import pytest

from customer_bot.api.deps import clear_dependency_caches
from customer_bot.config import Settings


@pytest.fixture(autouse=True)
def _clear_di_caches() -> None:
    clear_dependency_caches()


@pytest.fixture
def settings_factory(tmp_path: Path):
    def _build(**overrides: object) -> Settings:
        base_data: dict[str, object] = {
            "api_host": "127.0.0.1",
            "api_port": 9000,
            "api_max_user_message_length": 500,
            "api_cors_allow_origins": [
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            ],
            "api_cors_allow_credentials": False,
            "api_cors_allow_methods": ["GET", "POST"],
            "api_cors_allow_headers": ["Content-Type", "X-Request-ID"],
            "api_trusted_hosts": ["127.0.0.1", "localhost", "testserver"],
            "api_chat_rate_limit": "10/minute",
            "llm_provider": "ollama",
            "embedding_provider": "ollama",
            "OPENAI_API_KEY": "sk-test-openai",
            "openai_llm_model": "gpt-4o-mini",
            "openai_llm_temperature": None,
            "openai_llm_max_completion_tokens": None,
            "openai_llm_max_retries": None,
            "openai_llm_timeout_seconds": None,
            "openai_llm_api_base": None,
            "openai_llm_api_version": None,
            "openai_llm_strict": None,
            "openai_llm_reasoning_effort": None,
            "openai_embedding_model": "text-embedding-3-small",
            "openai_embedding_mode": None,
            "openai_embedding_batch_size": None,
            "openai_embedding_dimensions": None,
            "openai_embedding_max_retries": None,
            "openai_embedding_timeout_seconds": None,
            "openai_embedding_api_base": None,
            "openai_embedding_api_version": None,
            "openai_embedding_num_workers": None,
            "ollama_base_url": None,
            "ollama_chat_model": "qwen3.5:2b",
            "ollama_embedding_model": "qwen3-embedding:0.6b",
            "ollama_temperature": None,
            "ollama_request_timeout_seconds": None,
            "ollama_prompt_key": None,
            "ollama_json_mode": None,
            "ollama_thinking": None,
            "ollama_context_window": None,
            "ollama_keep_alive": "",  # don't keep alive connection for tests
            "ollama_embedding_batch_size": None,
            "ollama_embedding_keep_alive": None,
            "ollama_embedding_query_instruction": None,
            "ollama_embedding_text_instruction": None,
            "ollama_embedding_num_ctx": 2048,
            "chroma_persist_dir": tmp_path / "chroma",
            "faq_collection_name": "test_collection",
            "products_collection_name": "test_products_collection",
            "faq_corpus_csv_path": tmp_path / "corpus.csv",
            "products_corpus_csv_path": tmp_path / "products.csv",
            "faq_text_ingestion_mode": "question_only",
            "faq_retrieval_top_k": 3,
            "faq_similarity_cutoff": 0.60,
            "products_retrieval_top_k": 3,
            "products_similarity_cutoff": 0.70,
            "memory_max_turns": 10,
            "agent_description": "Agent for FAQ and product responses",
            "agent_system_prompt": (
                "You are a customer support assistant. "
                "Use the faq_lookup tool for FAQ information. "
                "Use the product_lookup tool for product information. "
                "You may answer a follow-up without calling the tool only when "
                "the needed information is already grounded in the chat history. "
                "The tool returns JSON with `matches`, where each item has "
                "grounded fields for that tool. "
                "Write a concise German answer using only information grounded "
                "in tool results or prior chat history grounded in those results. "
                "Do not invent product details, policies, or guarantees."
            ),
            "employee_request_instruction": (
                "If the user asks for a human agent before a guardrail handoff, "
                "use one short German reply that stays close to the pattern "
                "'Before I pass you to a human advisor, maybe I can help? I can "
                "answer questions about products, orders, shipping, returns, "
                "payments, privacy, or support processes. What is it about?', do "
                "not promise handoff, do not claim that handoff is impossible, "
                "and do not ask for order numbers, customer numbers, or contact details."
            ),
            "no_match_instruction": (
                "If `faq_lookup` or `product_lookup` returns an empty `matches` list, "
                "explain in German that you could not find reliable information for "
                "the request, do not claim there was a technical error, and ask "
                "exactly one helpful follow-up question that matches the missing detail."
            ),
            "faq_tool_description": (
                "Find top FAQ matches for a user question after similarity filtering. "
                "Returns JSON with a `matches` list containing `faq_id`, `answer`, and `score`."
            ),
            "product_tool_description": (
                "Find top product matches for a query after similarity filtering. "
                "Returns JSON with a `matches` list containing product fields and `score`."
            ),
            "agent_timeout_seconds": 45.0,
            "error_fallback_text": "Technischer Fehler.",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LANGFUSE_HOST": "http://localhost:3000",
            "LANGFUSE_TRACING_ENVIRONMENT": "default",
            "LANGFUSE_RELEASE": "",
            "langfuse_fail_fast": False,
        }
        base_data.update(overrides)
        return Settings(**base_data)

    return _build
