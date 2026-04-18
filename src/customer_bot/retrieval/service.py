from __future__ import annotations

from llama_index.core import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor

from customer_bot.config import Settings
from customer_bot.llama import create_embedding_model
from customer_bot.retrieval.backend import (
    ChromaVectorBackend,
    VectorBackendUnavailableError,
    VectorStoreBackend,
)
from customer_bot.retrieval.types import RetrievalHit, RetrievalResult


class RetrievalBootstrapError(RuntimeError):
    """Raised when the retrieval layer cannot be initialized."""


class FaqRetrieverService:
    def __init__(
        self,
        settings: Settings,
        embed_model: BaseEmbedding | None = None,
        index: VectorStoreIndex | None = None,
        postprocessor: SimilarityPostprocessor | None = None,
        vector_backend: VectorStoreBackend | None = None,
    ) -> None:
        self._settings = settings
        self._embed_model = embed_model or create_embedding_model(settings)
        self._index = index
        self._postprocessor = postprocessor or SimilarityPostprocessor(
            similarity_cutoff=settings.similarity_cutoff
        )
        self._vector_backend = vector_backend or ChromaVectorBackend(settings)

    def retrieve_best_answer(self, query: str) -> RetrievalResult:
        if not query.strip():
            return RetrievalResult()

        index = self._index or self._load_index()
        retriever = index.as_retriever(similarity_top_k=self._settings.retrieval_top_k)
        candidate_nodes = retriever.retrieve(query)
        filtered_nodes = self._postprocessor.postprocess_nodes(candidate_nodes, query_str=query)

        hits: list[RetrievalHit] = []
        for node in filtered_nodes:
            metadata = node.node.metadata or {}
            answer = str(metadata.get("answer", "")).strip()
            faq_id = str(metadata.get("faq_id", "")).strip()
            if not answer or not faq_id:
                continue

            hits.append(
                RetrievalHit(
                    faq_id=faq_id,
                    answer=answer,
                    score=node.score,
                )
            )

        return RetrievalResult(hits=hits)

    def _load_index(self) -> VectorStoreIndex:
        try:
            vector_store = self._vector_backend.load_query_vector_store()
        except VectorBackendUnavailableError as exc:
            raise RetrievalBootstrapError(
                "Vector store collection is unavailable. Run `uv run customer-bot-ingest` first."
            ) from exc

        self._index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=self._embed_model,
        )
        return self._index
