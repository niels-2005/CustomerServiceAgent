from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from customer_bot.agent.service import AgentService
from customer_bot.chat.service import ChatService
from customer_bot.memory.backend import InMemorySessionMemoryBackend
from customer_bot.retrieval.ingestion import IngestionService
from customer_bot.retrieval.service import FaqRetrieverService, ProductRetrieverService


def _ensure_ollama_ready(base_url: str, chat_model: str, embedding_model: str) -> None:
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Ollama not reachable at {base_url}: {exc}")

    payload = response.json()
    model_names = {item.get("name", "") for item in payload.get("models", [])}

    required = [chat_model, embedding_model]
    for model in required:
        if model not in model_names and f"{model}:latest" not in model_names:
            pytest.skip(f"Required Ollama model not available locally: {model}")


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.filterwarnings("ignore::pydantic.warnings.PydanticDeprecationWarning")
def test_chat_e2e_with_local_ollama(settings_factory, tmp_path: Path) -> None:
    settings = settings_factory(
        faq_corpus_csv_path=tmp_path / "corpus.csv",
        chroma_persist_dir=tmp_path / "chroma",
        langfuse_fail_fast=False,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    if settings.selectors.llm != "ollama" or settings.selectors.embedding != "ollama":
        pytest.skip("This integration test only supports ollama providers.")

    _ensure_ollama_ready(
        settings.llm.ollama.base_url,
        settings.llm.ollama.chat_model,
        settings.embedding.ollama.model,
    )

    settings.ingestion.faq.corpus_csv_path.write_text(
        "faq_id,question,answer\n"
        "faq_1,Wie kann ich ein Konto erstellen?,"
        "Du kannst ein Konto erstellen, indem du auf Registrieren klickst.\n",
        encoding="utf-8",
    )

    IngestionService(settings=settings).ingest()
    retriever = FaqRetrieverService(settings=settings)
    product_retriever = ProductRetrieverService(settings=settings)
    agent = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
    )
    chat_service = ChatService(
        memory_backend=InMemorySessionMemoryBackend(max_turns=settings.memory.max_turns),
        agent_service=agent,
    )

    result = asyncio.run(chat_service.chat("Wie kann ich ein Konto erstellen?"))

    assert isinstance(result.answer, str)
    assert result.answer.strip() != ""
    assert result.session_id
