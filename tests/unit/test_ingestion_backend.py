from __future__ import annotations

from pathlib import Path

import pytest
from llama_index.core.embeddings import MockEmbedding

from customer_bot.retrieval.ingestion import IngestionService


class FakeVectorBackend:
    def __init__(self, resource_name: str = "fake_backend_resource") -> None:
        self.build_calls = 0
        self._resource_name = resource_name

    @property
    def resource_name(self) -> str:
        return self._resource_name

    def build_ingestion_vector_store(self):
        self.build_calls += 1
        return "fake_store"

    def load_query_vector_store(self):
        raise NotImplementedError


@pytest.mark.unit
def test_ingestion_service_uses_injected_vector_backend(
    settings_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    corpus_path = tmp_path / "corpus.csv"
    corpus_path.write_text(
        "faq_id,question,answer\nfaq_1,Wie geht Login?,Nutze den Login Button.\n",
        encoding="utf-8",
    )
    settings = settings_factory(faq_corpus_csv_path=corpus_path)
    backend = FakeVectorBackend()
    captured: dict[str, object] = {}

    def _fake_from_defaults(cls, vector_store=None, **kwargs):
        captured["vector_store"] = vector_store
        return "fake_storage_context"

    class DummyVectorStoreIndex:
        def __init__(self, *, nodes, storage_context, embed_model, show_progress):
            captured["nodes"] = nodes
            captured["storage_context"] = storage_context
            captured["embed_model"] = embed_model
            captured["show_progress"] = show_progress

    monkeypatch.setattr(
        "customer_bot.retrieval.ingestion.StorageContext.from_defaults",
        classmethod(_fake_from_defaults),
    )
    monkeypatch.setattr("customer_bot.retrieval.ingestion.VectorStoreIndex", DummyVectorStoreIndex)

    service = IngestionService(
        settings=settings,
        embed_model=MockEmbedding(embed_dim=8),
        vector_backend=backend,
    )
    result = service.ingest()

    assert backend.build_calls == 1
    assert result.records_ingested == 1
    assert result.collection_name == "fake_backend_resource"
    assert captured["vector_store"] == "fake_store"
    assert captured["storage_context"] == "fake_storage_context"
    assert captured["show_progress"] is False
    nodes = captured["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) == 1
    assert nodes[0].metadata == {
        "faq_id": "faq_1",
        "question": "Wie geht Login?",
        "answer": "Nutze den Login Button.",
    }


@pytest.mark.unit
def test_ingestion_service_uses_product_collection_for_product_ingest(
    settings_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    product_path = tmp_path / "products.csv"
    product_path.write_text(
        "product_id,name,description,price,currency\nprod_1,Becher,Haelt warm,14.99,EUR\n",
        encoding="utf-8",
    )
    settings = settings_factory(products_corpus_csv_path=product_path)
    backend = FakeVectorBackend(resource_name="products_backend_resource")
    captured: dict[str, object] = {}

    def _fake_from_defaults(cls, vector_store=None, **kwargs):
        captured["vector_store"] = vector_store
        return "fake_storage_context"

    class DummyVectorStoreIndex:
        def __init__(self, *, nodes, storage_context, embed_model, show_progress):
            captured["nodes"] = nodes
            captured["storage_context"] = storage_context
            captured["embed_model"] = embed_model
            captured["show_progress"] = show_progress

    monkeypatch.setattr(
        "customer_bot.retrieval.ingestion.StorageContext.from_defaults",
        classmethod(_fake_from_defaults),
    )
    monkeypatch.setattr("customer_bot.retrieval.ingestion.VectorStoreIndex", DummyVectorStoreIndex)

    service = IngestionService(
        settings=settings,
        embed_model=MockEmbedding(embed_dim=8),
        product_vector_backend=backend,
    )
    result = service.ingest(source="products")

    assert backend.build_calls == 1
    assert result.records_ingested == 1
    assert result.collection_name == "products_backend_resource"
    nodes = captured["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) == 1
    assert nodes[0].metadata == {
        "product_id": "prod_1",
        "name": "Becher",
        "description": "Haelt warm",
        "category": "",
        "price": "14.99",
        "currency": "EUR",
        "availability": "",
        "features": "",
        "url": "",
    }
