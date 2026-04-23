from __future__ import annotations

from llama_index.core import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor

from customer_bot.config import Settings
from customer_bot.model_factory import create_embedding_model
from customer_bot.retrieval.backend import (
    ChromaVectorBackend,
    VectorBackendUnavailableError,
    VectorStoreBackend,
)
from customer_bot.retrieval.types import (
    ProductRetrievalHit,
    ProductRetrievalResult,
    RetrievalHit,
    RetrievalResult,
)


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
            similarity_cutoff=settings.faq_similarity_cutoff
        )
        self._vector_backend = vector_backend or ChromaVectorBackend(settings)

    def retrieve_best_answer(self, query: str) -> RetrievalResult:
        if not query.strip():
            return RetrievalResult()

        index = self._index or self._load_index()
        retriever = index.as_retriever(similarity_top_k=self._settings.faq_retrieval_top_k)
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


class ProductRetrieverService:
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
            similarity_cutoff=settings.products_similarity_cutoff
        )
        self._vector_backend = vector_backend or ChromaVectorBackend(
            settings,
            collection_name=settings.products_collection_name,
        )

    def retrieve_products(self, query: str) -> ProductRetrievalResult:
        if not query.strip():
            return ProductRetrievalResult()

        index = self._index or self._load_index()
        retriever = index.as_retriever(similarity_top_k=self._settings.products_retrieval_top_k)
        candidate_nodes = retriever.retrieve(query)
        filtered_nodes = self._postprocessor.postprocess_nodes(candidate_nodes, query_str=query)

        hits: list[ProductRetrievalHit] = []
        for node in filtered_nodes:
            metadata = node.node.metadata or {}
            product_id = str(metadata.get("product_id", "")).strip()
            name = str(metadata.get("name", "")).strip()
            description = str(metadata.get("description", "")).strip()
            if not product_id or not name or not description:
                continue

            hits.append(
                ProductRetrievalHit(
                    product_id=product_id,
                    name=name,
                    description=description,
                    category=str(metadata.get("category", "")).strip(),
                    price=str(metadata.get("price", "")).strip(),
                    currency=str(metadata.get("currency", "")).strip(),
                    availability=str(metadata.get("availability", "")).strip(),
                    features=str(metadata.get("features", "")).strip(),
                    url=str(metadata.get("url", "")).strip(),
                    score=node.score,
                )
            )

        return ProductRetrievalResult(hits=hits)

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
