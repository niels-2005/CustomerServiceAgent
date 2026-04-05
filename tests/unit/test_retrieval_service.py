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

    def as_retriever(self, similarity_top_k: int):
        return FakeRetriever(self._nodes)


class FakePostprocessor:
    def __init__(self, nodes: list[NodeWithScore]) -> None:
        self._nodes = nodes

    def postprocess_nodes(self, nodes, query_str: str):
        return self._nodes


@pytest.mark.unit
def test_retrieval_service_returns_best_answer(settings_factory) -> None:
    node = TextNode(
        text="Frage: Wie registriere ich mich?",
        metadata={"faq_id": "faq_1", "answer": "Klicke auf Registrieren."},
    )
    scored = NodeWithScore(node=node, score=0.9)
    service = FaqRetrieverService(
        settings=settings_factory(),
        embed_model=MockEmbedding(embed_dim=8),
        index=FakeIndex([scored]),
        postprocessor=FakePostprocessor([scored]),
    )

    result = service.retrieve_best_answer("Wie registriere ich mich?")

    assert result.answer == "Klicke auf Registrieren."
    assert result.faq_id == "faq_1"


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

    assert result.answer is None
    assert result.faq_id is None
    assert result.score is None
