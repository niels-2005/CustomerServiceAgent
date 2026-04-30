from __future__ import annotations

from pathlib import Path

import chromadb
import pytest
from llama_index.core.embeddings import MockEmbedding

from customer_bot.retrieval.ingestion import IngestionService
from customer_bot.retrieval.service import (
    FaqRetrieverService,
    ProductRetrieverService,
    RetrievalBootstrapError,
)

KEYWORD_VOCAB = (
    "konto",
    "registrieren",
    "passwort",
    "lieferung",
    "retoure",
    "laptop",
    "akku",
    "premium",
)


class KeywordEmbedding(MockEmbedding):
    """Deterministic keyword embedding used by offline integration tests."""

    def __init__(self) -> None:
        super().__init__(embed_dim=len(KEYWORD_VOCAB))

    def _encode(self, text: str) -> list[float]:
        lowered = text.lower()
        return [1.0 if keyword in lowered else 0.0 for keyword in KEYWORD_VOCAB]

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._encode(text)

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._encode(query)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._encode(text)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._encode(query)


def _use_ephemeral_chroma(monkeypatch: pytest.MonkeyPatch):
    """Route Chroma HTTP client creation to a shared in-memory test client."""
    client = chromadb.EphemeralClient()
    monkeypatch.setattr(
        "customer_bot.retrieval.backend.chromadb.HttpClient",
        lambda host, port: client,
    )
    return client


@pytest.mark.integration
def test_faq_ingest_then_retrieve_best_answer(
    settings_factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_ephemeral_chroma(monkeypatch)
    corpus_path = tmp_path / "faq.csv"
    corpus_path.write_text(
        "faq_id,question,answer\n"
        "faq_register,Wie kann ich mein Konto registrieren?,"
        "Nutze den Button Konto registrieren.\n"
        "faq_return,Wie starte ich eine Retoure?,"
        "Nutze das Retourenportal in deinem Konto.\n",
        encoding="utf-8",
    )
    settings = settings_factory(faq_corpus_csv_path=corpus_path, faq_similarity_cutoff=0.2)
    embedding = KeywordEmbedding()

    IngestionService(settings=settings, embed_model=embedding).ingest(source="faq")
    result = FaqRetrieverService(settings=settings, embed_model=embedding).retrieve_best_answer(
        "konto registrieren"
    )

    assert len(result.hits) == 1
    assert result.hits[0].faq_id == "faq_register"
    assert result.hits[0].answer == "Nutze den Button Konto registrieren."


@pytest.mark.integration
def test_product_ingest_then_retrieve_product(
    settings_factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_ephemeral_chroma(monkeypatch)
    products_path = tmp_path / "products.csv"
    products_path.write_text(
        "product_id,name,description,category,price,currency,availability,features,url\n"
        "prod_laptop,Nexa Laptop,Premium Laptop mit starkem Akku,Elektronik,1499,EUR,"
        "in_stock,akku|premium,https://example.test/laptop\n"
        "prod_mouse,Nexa Mouse,Leichte Maus fuer unterwegs,Zubehoer,39,EUR,"
        "in_stock,leicht|mobil,https://example.test/mouse\n",
        encoding="utf-8",
    )
    settings = settings_factory(
        products_corpus_csv_path=products_path,
        products_similarity_cutoff=0.2,
    )
    embedding = KeywordEmbedding()

    IngestionService(settings=settings, embed_model=embedding).ingest(source="products")
    result = ProductRetrieverService(settings=settings, embed_model=embedding).retrieve_products(
        "premium laptop akku"
    )

    assert len(result.hits) == 1
    assert result.hits[0].product_id == "prod_laptop"
    assert result.hits[0].name == "Nexa Laptop"
    assert result.hits[0].description == "Premium Laptop mit starkem Akku"


@pytest.mark.integration
def test_faq_and_product_ingestion_stay_separate(
    settings_factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_ephemeral_chroma(monkeypatch)
    faq_path = tmp_path / "faq.csv"
    faq_path.write_text(
        "faq_id,question,answer\n"
        "faq_return,Wie starte ich eine Retoure?,Nutze das Retourenportal.\n",
        encoding="utf-8",
    )
    products_path = tmp_path / "products.csv"
    products_path.write_text(
        "product_id,name,description\nprod_laptop,Nexa Laptop,Premium Laptop mit starkem Akku\n",
        encoding="utf-8",
    )
    settings = settings_factory(
        faq_corpus_csv_path=faq_path,
        products_corpus_csv_path=products_path,
        faq_similarity_cutoff=0.2,
        products_similarity_cutoff=0.2,
    )
    embedding = KeywordEmbedding()
    service = IngestionService(settings=settings, embed_model=embedding)

    service.ingest(source="faq")
    service.ingest(source="products")

    faq_result = FaqRetrieverService(settings=settings, embed_model=embedding).retrieve_best_answer(
        "premium laptop"
    )
    product_result = ProductRetrieverService(
        settings=settings,
        embed_model=embedding,
    ).retrieve_products("retoure")

    assert faq_result.hits == []
    assert product_result.hits == []


@pytest.mark.integration
def test_retrieval_requires_existing_collection(
    settings_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingCollectionClient:
        def get_collection(self, *, name: str):
            raise RuntimeError(f"missing {name}")

    monkeypatch.setattr(
        "customer_bot.retrieval.backend.chromadb.HttpClient",
        lambda host, port: MissingCollectionClient(),
    )
    settings = settings_factory(faq_similarity_cutoff=0.2)

    with pytest.raises(RetrievalBootstrapError, match="customer-bot-ingest"):
        FaqRetrieverService(
            settings=settings,
            embed_model=KeywordEmbedding(),
        ).retrieve_best_answer("konto registrieren")


@pytest.mark.integration
def test_full_rebuild_replaces_old_collection_contents(
    settings_factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _use_ephemeral_chroma(monkeypatch)
    corpus_path = tmp_path / "faq.csv"
    corpus_path.write_text(
        "faq_id,question,answer\n"
        "faq_register,Wie kann ich mein Konto registrieren?,Registriere dich ueber den Link.\n",
        encoding="utf-8",
    )
    settings = settings_factory(faq_corpus_csv_path=corpus_path, faq_similarity_cutoff=0.2)
    embedding = KeywordEmbedding()
    service = IngestionService(settings=settings, embed_model=embedding)

    first = service.ingest(source="faq")

    corpus_path.write_text(
        "faq_id,question,answer\n"
        "faq_shipping,Wie lange dauert die Lieferung?,Die Lieferung dauert zwei Tage.\n",
        encoding="utf-8",
    )
    second = service.ingest(source="faq")
    retriever = FaqRetrieverService(settings=settings, embed_model=embedding)
    collection = client.get_collection(name=settings.storage.faq.collection_name)

    assert first.records_ingested == 1
    assert second.records_ingested == 1
    assert collection.count() == 1
    assert retriever.retrieve_best_answer("konto registrieren").hits == []
    rebuilt = retriever.retrieve_best_answer("lieferung")
    assert len(rebuilt.hits) == 1
    assert rebuilt.hits[0].faq_id == "faq_shipping"
