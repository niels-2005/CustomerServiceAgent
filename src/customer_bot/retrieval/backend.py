"""Vector-store backend abstractions and the default Chroma implementation."""

from __future__ import annotations

from typing import Protocol

import chromadb
from chromadb.api import ClientAPI
from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.vector_stores.chroma import ChromaVectorStore

from customer_bot.config import Settings


class VectorBackendUnavailableError(RuntimeError):
    """Raised when a vector backend cannot provide the query store."""


class VectorStoreBackend(Protocol):
    @property
    def resource_name(self) -> str:
        """Human-readable backend resource identifier (e.g. collection name)."""
        ...

    def build_ingestion_vector_store(self) -> BasePydanticVectorStore:
        """Return a vector store prepared for deterministic ingestion rebuilds."""
        ...

    def load_query_vector_store(self) -> BasePydanticVectorStore:
        """Return an existing vector store for retrieval queries."""
        ...


class ChromaVectorBackend(VectorStoreBackend):
    """Chroma-backed vector store implementation for retrieval and ingestion."""

    def __init__(self, settings: Settings, *, collection_name: str | None = None) -> None:
        self._settings = settings
        self._collection_name = collection_name or settings.storage.faq.collection_name

    @property
    def resource_name(self) -> str:
        """Return the configured Chroma collection name."""
        return self._collection_name

    def build_ingestion_vector_store(self) -> BasePydanticVectorStore:
        """Return a clean collection for deterministic ingestion rebuilds."""
        client = self._create_client()

        try:
            client.delete_collection(name=self._collection_name)
        except Exception:
            # A missing collection is fine for a first run.
            pass

        collection = client.get_or_create_collection(name=self._collection_name)
        return ChromaVectorStore(chroma_collection=collection)

    def load_query_vector_store(self) -> BasePydanticVectorStore:
        """Return the existing collection used for retrieval queries."""
        client = self._create_client()
        try:
            collection = client.get_collection(name=self._collection_name)
        except Exception as exc:
            raise VectorBackendUnavailableError(
                "Vector store collection is unavailable. Run `uv run customer-bot-ingest` first."
            ) from exc
        return ChromaVectorStore(chroma_collection=collection)

    def _create_client(self) -> ClientAPI:
        """Create a persistent Chroma client for the configured storage path."""
        return chromadb.PersistentClient(path=str(self._settings.storage.chroma_persist_dir))
