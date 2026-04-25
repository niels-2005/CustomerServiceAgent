"""Unit tests for FAQ and product retrieval filtering and bootstrap behavior."""

from __future__ import annotations

import pytest
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import NodeWithScore, TextNode

from customer_bot.retrieval.backend import VectorBackendUnavailableError
from customer_bot.retrieval.service import (
    FaqRetrieverService,
    ProductRetrieverService,
    RetrievalBootstrapError,
)


class FakeRetriever:
    def __init__(self, nodes: list[NodeWithScore]) -> None:
        self._nodes = nodes

    def retrieve(self, query: str) -> list[NodeWithScore]:
        return self._nodes


class FakeIndex:
    def __init__(self, nodes: list[NodeWithScore]) -> None:
        self._nodes = nodes
        self.last_similarity_top_k: int | None = None

    def as_retriever(self, similarity_top_k: int):
        self.last_similarity_top_k = similarity_top_k
        return FakeRetriever(self._nodes)


class FakePostprocessor:
    def __init__(self, nodes: list[NodeWithScore]) -> None:
        self._nodes = nodes

    def postprocess_nodes(self, nodes, query_str: str):
        return self._nodes


class FakeVectorBackend:
    def __init__(self, nodes: list[NodeWithScore], should_fail: bool = False) -> None:
        self._nodes = nodes
        self._should_fail = should_fail
        self.load_calls = 0

    @property
    def resource_name(self) -> str:
        return "fake_collection"

    def build_ingestion_vector_store(self):
        raise NotImplementedError

    def load_query_vector_store(self):
        self.load_calls += 1
        if self._should_fail:
            raise VectorBackendUnavailableError("backend unavailable")
        return self

    def as_retriever(self, similarity_top_k: int):
        return FakeRetriever(self._nodes)


@pytest.mark.unit
def test_retrieval_service_returns_filtered_hits(settings_factory) -> None:
    node_1 = TextNode(
        text="Frage: Wie registriere ich mich?",
        metadata={"faq_id": "faq_1", "answer": "Klicke auf Registrieren."},
    )
    node_2 = TextNode(
        text="Frage: Wie melde ich mich an?",
        metadata={"faq_id": "faq_2", "answer": "Nutze deine Zugangsdaten."},
    )
    scored_1 = NodeWithScore(node=node_1, score=0.9)
    scored_2 = NodeWithScore(node=node_2, score=0.81)
    fake_index = FakeIndex([scored_1, scored_2])
    service = FaqRetrieverService(
        settings=settings_factory(faq_retrieval_top_k=3),
        embed_model=MockEmbedding(embed_dim=8),
        index=fake_index,
        postprocessor=FakePostprocessor([scored_1, scored_2]),
    )

    result = service.retrieve_best_answer("Wie registriere ich mich?")

    assert fake_index.last_similarity_top_k == 3
    assert [(hit.faq_id, hit.answer, hit.score) for hit in result.hits] == [
        ("faq_1", "Klicke auf Registrieren.", 0.9),
        ("faq_2", "Nutze deine Zugangsdaten.", 0.81),
    ]


@pytest.mark.unit
def test_retrieval_service_returns_no_match(settings_factory) -> None:
    node = TextNode(
        text="Frage: Irgendwas",
        metadata={"faq_id": "faq_2", "answer": "Antwort."},
    )
    scored = NodeWithScore(node=node, score=0.2)
    service = FaqRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        index=FakeIndex([scored]),
        postprocessor=FakePostprocessor([]),
    )

    result = service.retrieve_best_answer("Fremdes Thema")

    assert result.hits == []


@pytest.mark.unit
def test_retrieval_service_returns_empty_for_blank_query(settings_factory) -> None:
    service = FaqRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        index=FakeIndex([]),
        postprocessor=FakePostprocessor([]),
    )

    result = service.retrieve_best_answer("   ")

    assert result.hits == []


@pytest.mark.unit
def test_retrieval_service_skips_nodes_missing_required_metadata(settings_factory) -> None:
    valid_node = TextNode(
        text="Frage: Passwort vergessen?",
        metadata={"faq_id": "faq_valid", "answer": "Nutze Passwort vergessen."},
    )
    missing_answer = TextNode(
        text="Frage: X",
        metadata={"faq_id": "faq_missing_answer"},
    )
    missing_faq_id = TextNode(
        text="Frage: Y",
        metadata={"answer": "Antwort ohne ID"},
    )
    scored_valid = NodeWithScore(node=valid_node, score=0.87)
    scored_missing_answer = NodeWithScore(node=missing_answer, score=0.85)
    scored_missing_faq_id = NodeWithScore(node=missing_faq_id, score=0.84)

    service = FaqRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        index=FakeIndex([scored_valid, scored_missing_answer, scored_missing_faq_id]),
        postprocessor=FakePostprocessor(
            [scored_valid, scored_missing_answer, scored_missing_faq_id]
        ),
    )

    result = service.retrieve_best_answer("Passwort")

    assert [(hit.faq_id, hit.answer, hit.score) for hit in result.hits] == [
        ("faq_valid", "Nutze Passwort vergessen.", 0.87)
    ]


@pytest.mark.unit
def test_retrieval_service_uses_vector_backend_to_bootstrap_index(
    settings_factory, monkeypatch
) -> None:
    node = TextNode(
        text="Frage: Wie registriere ich mich?",
        metadata={"faq_id": "faq_1", "answer": "Klicke auf Registrieren."},
    )
    scored = NodeWithScore(node=node, score=0.9)
    backend = FakeVectorBackend([scored])

    fake_index = FakeIndex([scored])
    captured: dict[str, object] = {}

    def _fake_from_vector_store(cls, vector_store, embed_model=None, **kwargs):
        captured["vector_store"] = vector_store
        captured["embed_model"] = embed_model
        return fake_index

    monkeypatch.setattr(
        "customer_bot.retrieval.service.VectorStoreIndex.from_vector_store",
        classmethod(_fake_from_vector_store),
    )

    service = FaqRetrieverService(
        settings=settings_factory(faq_retrieval_top_k=1),
        embed_model=MockEmbedding(embed_dim=8),
        vector_backend=backend,
        postprocessor=FakePostprocessor([scored]),
    )

    first = service.retrieve_best_answer("Wie registriere ich mich?")
    second = service.retrieve_best_answer("Wie registriere ich mich?")

    # The vector backend should only be used for the initial lazy bootstrap.
    assert [(hit.faq_id, hit.answer, hit.score) for hit in first.hits] == [
        ("faq_1", "Klicke auf Registrieren.", 0.9)
    ]
    assert [(hit.faq_id, hit.answer, hit.score) for hit in second.hits] == [
        ("faq_1", "Klicke auf Registrieren.", 0.9)
    ]
    assert backend.load_calls == 1
    assert captured["vector_store"] is backend
    assert isinstance(captured["embed_model"], MockEmbedding)


@pytest.mark.unit
def test_retrieval_service_raises_bootstrap_error_when_backend_unavailable(
    settings_factory,
) -> None:
    backend = FakeVectorBackend([], should_fail=True)
    service = FaqRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        vector_backend=backend,
    )

    with pytest.raises(
        RetrievalBootstrapError,
        match="Vector store collection is unavailable. Run `uv run customer-bot-ingest` first.",
    ):
        service.retrieve_best_answer("Frage")


@pytest.mark.unit
def test_product_retrieval_service_returns_filtered_hits(settings_factory) -> None:
    node = TextNode(
        text="Produkt: Becher",
        metadata={
            "product_id": "prod_1",
            "name": "Becher",
            "description": "Haelt warm.",
            "category": "lifestyle",
            "price": "14.99",
            "currency": "EUR",
            "availability": "available",
            "features": "Isoliert|Stylisch",
            "url": "https://example.com/becher",
        },
    )
    scored = NodeWithScore(node=node, score=0.93)
    fake_index = FakeIndex([scored])
    service = ProductRetrieverService(
        settings=settings_factory(products_retrieval_top_k=2),
        embed_model=MockEmbedding(embed_dim=8),
        index=fake_index,
        postprocessor=FakePostprocessor([scored]),
    )

    result = service.retrieve_products("Welcher Becher haelt warm?")

    assert fake_index.last_similarity_top_k == 2
    assert [(hit.product_id, hit.name, hit.description, hit.score) for hit in result.hits] == [
        ("prod_1", "Becher", "Haelt warm.", 0.93)
    ]


@pytest.mark.unit
def test_product_retrieval_service_skips_nodes_missing_required_metadata(settings_factory) -> None:
    valid_node = TextNode(
        text="Produkt: Becher",
        metadata={
            "product_id": "prod_1",
            "name": "Becher",
            "description": "Haelt warm.",
        },
    )
    missing_name = TextNode(
        text="Produkt: X",
        metadata={"product_id": "prod_2", "description": "Beschreibung"},
    )
    missing_description = TextNode(
        text="Produkt: Y",
        metadata={"product_id": "prod_3", "name": "Lampe"},
    )
    scored_valid = NodeWithScore(node=valid_node, score=0.87)
    scored_missing_name = NodeWithScore(node=missing_name, score=0.85)
    scored_missing_description = NodeWithScore(node=missing_description, score=0.84)

    service = ProductRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        index=FakeIndex([scored_valid, scored_missing_name, scored_missing_description]),
        postprocessor=FakePostprocessor(
            [scored_valid, scored_missing_name, scored_missing_description]
        ),
    )

    result = service.retrieve_products("Produkt")

    assert [(hit.product_id, hit.name) for hit in result.hits] == [("prod_1", "Becher")]


@pytest.mark.unit
def test_product_retrieval_service_returns_empty_for_blank_query(settings_factory) -> None:
    service = ProductRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        index=FakeIndex([]),
        postprocessor=FakePostprocessor([]),
    )

    result = service.retrieve_products("  ")

    assert result.hits == []


@pytest.mark.unit
def test_product_retrieval_service_raises_bootstrap_error_when_backend_unavailable(
    settings_factory,
) -> None:
    backend = FakeVectorBackend([], should_fail=True)
    service = ProductRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        vector_backend=backend,
    )

    with pytest.raises(
        RetrievalBootstrapError,
        match="Vector store collection is unavailable. Run `uv run customer-bot-ingest` first.",
    ):
        service.retrieve_products("Produkt")
