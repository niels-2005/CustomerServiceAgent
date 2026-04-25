from __future__ import annotations

import sys
from pathlib import Path

import chromadb
import pytest
from llama_index.core.embeddings import MockEmbedding

from customer_bot.ingest.cli import main


@pytest.mark.integration
def test_customer_bot_ingest_cli_builds_collection_for_selected_source(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    corpus_path = tmp_path / "faq.csv"
    corpus_path.write_text(
        "faq_id,question,answer\n"
        "faq_register,Wie registriere ich mein Konto?,Nutze den Registrieren-Link.\n",
        encoding="utf-8",
    )
    settings = settings_factory(
        faq_corpus_csv_path=corpus_path,
        chroma_persist_dir=tmp_path / "chroma",
    )

    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr(
        "customer_bot.retrieval.ingestion.create_embedding_model",
        lambda settings: MockEmbedding(embed_dim=8),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["customer-bot-ingest", "--source", "faq", "--path", str(corpus_path)],
    )

    main()
    output = capsys.readouterr().out
    client = chromadb.PersistentClient(path=str(settings.storage.chroma_persist_dir))
    collection = client.get_collection(name=settings.storage.faq.collection_name)

    assert "Ingestion completed successfully" in output
    assert collection.count() == 1
