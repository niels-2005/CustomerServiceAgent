from __future__ import annotations

import pytest
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import NodeWithScore, TextNode

from customer_bot.retrieval.service import FaqRetrieverService


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
        settings=settings_factory(retrieval_top_k=3),
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
