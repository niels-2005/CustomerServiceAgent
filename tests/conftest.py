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
            "fallback_text": "Kein Treffer.",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LANGFUSE_HOST": "http://localhost:3000",
            "langfuse_fail_fast": False,
        }
        base_data.update(overrides)
        return Settings(**base_data)

    return _build
