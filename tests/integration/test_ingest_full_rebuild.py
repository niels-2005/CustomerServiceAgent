from __future__ import annotations

from pathlib import Path

import chromadb
import pytest
from llama_index.core.embeddings import MockEmbedding

from customer_bot.retrieval.ingestion import IngestionService


@pytest.mark.integration
def test_ingest_full_rebuild_is_idempotent(settings_factory, tmp_path: Path) -> None:
    corpus_path = tmp_path / "corpus.csv"
    corpus_path.write_text(
        "faq_id,question,answer\n"
        "faq_1,Wie registriere ich mich?,Klicke auf Registrieren.\n"
        "faq_2,Passwort vergessen?,Nutze Passwort vergessen.\n",
        encoding="utf-8",
    )

    settings = settings_factory(faq_corpus_csv_path=corpus_path)
    service = IngestionService(settings=settings, embed_model=MockEmbedding(embed_dim=8))

    first = service.ingest()
    second = service.ingest()

    client = chromadb.PersistentClient(path=str(settings.storage.chroma_persist_dir))
    collection = client.get_collection(name=settings.storage.faq.collection_name)

    assert first.records_ingested == 2
    assert second.records_ingested == 2
    assert collection.count() == 2
