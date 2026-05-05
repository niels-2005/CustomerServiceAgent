"""Retrieval services for FAQ answers and product records.

The services hide vector-store bootstrap details behind a small API and enforce
the metadata requirements expected by the rest of the application.
"""

from __future__ import annotations

import asyncio
import logging

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
    RetrievalPrefetchContext,
    RetrievalResult,
)

logger = logging.getLogger(__name__)


class RetrievalBootstrapError(RuntimeError):
    """Raised when the retrieval layer cannot be initialized."""


class FaqRetrieverService:
    """Retrieve FAQ answers from the configured vector store."""

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
            similarity_cutoff=settings.retrieval.faq.similarity_cutoff
        )
        self._vector_backend = vector_backend or ChromaVectorBackend(settings)

    def retrieve_best_answer(self, query: str) -> RetrievalResult:
        """Return filtered FAQ hits for the given query.

        Empty queries resolve to an empty result. Nodes missing required FAQ
        metadata are skipped so downstream code only sees valid hits.
        """
        if not query.strip():
            return RetrievalResult()

        index = self._index or self._load_index()
        retriever = index.as_retriever(similarity_top_k=self._settings.retrieval.faq.top_k)
        candidate_nodes = retriever.retrieve(query)
        filtered_nodes = self._postprocessor.postprocess_nodes(candidate_nodes, query_str=query)

        hits: list[RetrievalHit] = []
        for node in filtered_nodes:
            metadata = node.node.metadata or {}
            answer = str(metadata.get("answer", "")).strip()
            faq_id = str(metadata.get("faq_id", "")).strip()
            # Retrieval results are only valid if they preserve the FAQ contract
            # expected by tooling, tracing, and response generation.
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
        """Load and cache the FAQ index from the vector backend."""
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
    """Retrieve product records from the configured product collection."""

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
            similarity_cutoff=settings.retrieval.products.similarity_cutoff
        )
        self._vector_backend = vector_backend or ChromaVectorBackend(
            settings,
            collection_name=settings.storage.products.collection_name,
        )

    def retrieve_products(self, query: str) -> ProductRetrievalResult:
        """Return filtered product hits for the given query."""
        if not query.strip():
            return ProductRetrievalResult()

        index = self._index or self._load_index()
        retriever = index.as_retriever(similarity_top_k=self._settings.retrieval.products.top_k)
        candidate_nodes = retriever.retrieve(query)
        filtered_nodes = self._postprocessor.postprocess_nodes(candidate_nodes, query_str=query)

        hits: list[ProductRetrievalHit] = []
        for node in filtered_nodes:
            metadata = node.node.metadata or {}
            product_id = str(metadata.get("product_id", "")).strip()
            name = str(metadata.get("name", "")).strip()
            description = str(metadata.get("description", "")).strip()
            # The product tool expects these fields to exist on every hit.
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
        """Load and cache the product index from the vector backend."""
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


class RetrievalPrefetchService:
    """Run deterministic FAQ and product retrieval before agent execution.

    The prefetch stage is intentionally lightweight: it reuses the existing
    retrieval services, does not mutate conversation state, and degrades
    gracefully when one or both sources fail.
    """

    def __init__(
        self,
        faq_retriever: FaqRetrieverService,
        product_retriever: ProductRetrieverService,
    ) -> None:
        self._faq_retriever = faq_retriever
        self._product_retriever = product_retriever

    async def prefetch(self, query: str) -> RetrievalPrefetchContext:
        """Return request-local retrieval context for the given user query."""
        stripped_query = query.strip()
        if not stripped_query:
            return RetrievalPrefetchContext(query=query)

        faq_task = asyncio.to_thread(self._faq_retriever.retrieve_best_answer, stripped_query)
        product_task = asyncio.to_thread(self._product_retriever.retrieve_products, stripped_query)
        faq_result, product_result = await asyncio.gather(
            faq_task,
            product_task,
            return_exceptions=True,
        )

        context = RetrievalPrefetchContext(query=stripped_query)
        if isinstance(faq_result, Exception):
            logger.warning("FAQ retrieval prefetch failed: %s", faq_result)
            context.failed_sources.append("faq")
        else:
            context.faq_hits = faq_result.hits

        if isinstance(product_result, Exception):
            logger.warning("Product retrieval prefetch failed: %s", product_result)
            context.failed_sources.append("products")
        else:
            context.product_hits = product_result.hits

        return context
