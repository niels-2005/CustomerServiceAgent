from __future__ import annotations

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.vector_stores.chroma import ChromaVectorStore

from customer_bot.config import Settings
from customer_bot.llama import create_embedding_model
from customer_bot.retrieval.types import RetrievalResult


class RetrievalBootstrapError(RuntimeError):
    """Raised when the retrieval layer cannot be initialized."""


class FaqRetrieverService:
    def __init__(
        self,
        settings: Settings,
        embed_model: BaseEmbedding | None = None,
        index: VectorStoreIndex | None = None,
        postprocessor: SimilarityPostprocessor | None = None,
    ) -> None:
        self._settings = settings
        self._embed_model = embed_model or create_embedding_model(settings)
        self._index = index
        self._postprocessor = postprocessor or SimilarityPostprocessor(
            similarity_cutoff=settings.similarity_cutoff
        )

    def retrieve_best_answer(self, query: str) -> RetrievalResult:
        if not query.strip():
            return RetrievalResult(answer=None, faq_id=None, score=None)

        index = self._index or self._load_index()
        retriever = index.as_retriever(similarity_top_k=self._settings.retrieval_top_k)
        candidate_nodes = retriever.retrieve(query)
        filtered_nodes = self._postprocessor.postprocess_nodes(candidate_nodes, query_str=query)

        if not filtered_nodes:
            return RetrievalResult(answer=None, faq_id=None, score=None)

        best_node = filtered_nodes[0]
        answer = (best_node.node.metadata or {}).get("answer")
        faq_id = (best_node.node.metadata or {}).get("faq_id")

        if not answer:
            return RetrievalResult(answer=None, faq_id=faq_id, score=best_node.score)

        return RetrievalResult(answer=str(answer), faq_id=str(faq_id), score=best_node.score)

    def _load_index(self) -> VectorStoreIndex:
        try:
            client = chromadb.PersistentClient(path=str(self._settings.chroma_persist_dir))
            collection = client.get_collection(name=self._settings.chroma_collection_name)
        except Exception as exc:
            raise RetrievalBootstrapError(
                "Chroma collection is unavailable. Run `uv run customer-bot-ingest` first."
            ) from exc

        vector_store = ChromaVectorStore(chroma_collection=collection)
        self._index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=self._embed_model,
        )
        return self._index
