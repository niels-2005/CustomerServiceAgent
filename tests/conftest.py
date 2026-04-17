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
            "ollama_base_url": "http://localhost:11434",
            "ollama_chat_model": "qwen3.5:2b",
            "ollama_embedding_model": "qwen3-embedding:0.6b",
            "ollama_request_timeout_seconds": 360.0,
            "ollama_thinking": False,
            "ollama_context_window": 8000,
            "ollama_keep_alive": "",  # don't keep alive connection for tests
            "ollama_embedding_num_ctx": 2048,
            "chroma_persist_dir": tmp_path / "chroma",
            "chroma_collection_name": "test_collection",
            "corpus_csv_path": tmp_path / "corpus.csv",
            "text_ingestion_mode": "question_only",
            "retrieval_top_k": 3,
            "similarity_cutoff": 0.60,
            "memory_max_turns": 10,
            "agent_description": "Agent for FAQ-only customer support responses",
            "agent_system_prompt": (
                "You are a customer support FAQ assistant. "
                "Use the faq_lookup tool whenever you need new FAQ information "
                "to answer the user's message. "
                "You may answer a follow-up without calling the tool only when "
                "the needed information is already grounded in the chat history "
                "from earlier FAQ results. "
                "The tool returns JSON with `matches`, where each item has "
                "`faq_id`, `answer`, and `score`. "
                "Write a concise German answer using only information grounded "
                "in tool results or prior chat history grounded in those results. "
                "Do not invent product details, policies, or guarantees."
            ),
            "no_match_instruction": (
                "If `faq_lookup` returns an empty `matches` list, explain in German "
                "that you could not find reliable information in the FAQs, adapt "
                "the wording to the user's style, and offer a helpful next step "
                "such as contacting support. Do not claim there was a technical error."
            ),
            "faq_tool_description": (
                "Find top FAQ matches for a user question after similarity filtering. "
                "Returns JSON with a `matches` list containing `faq_id`, `answer`, and `score`."
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
