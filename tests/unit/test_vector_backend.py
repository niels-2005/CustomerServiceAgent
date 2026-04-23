from __future__ import annotations

import pytest

from customer_bot.retrieval.backend import ChromaVectorBackend, VectorBackendUnavailableError


@pytest.mark.unit
def test_chroma_vector_backend_build_ingestion_vector_store(settings_factory, monkeypatch) -> None:
    settings = settings_factory()
    calls: dict[str, object] = {}

    class FakeClient:
        def delete_collection(self, *, name: str) -> None:
            calls["deleted"] = name

        def get_or_create_collection(self, *, name: str):
            calls["created"] = name
            return {"name": name}

    def _fake_client_factory(path: str):
        calls["path"] = path
        return FakeClient()

    def _fake_chroma_vector_store(*, chroma_collection):
        calls["collection_obj"] = chroma_collection
        return {"vector_store": chroma_collection}

    monkeypatch.setattr(
        "customer_bot.retrieval.backend.chromadb.PersistentClient",
        _fake_client_factory,
    )
    monkeypatch.setattr(
        "customer_bot.retrieval.backend.ChromaVectorStore",
        _fake_chroma_vector_store,
    )

    backend = ChromaVectorBackend(settings)
    vector_store = backend.build_ingestion_vector_store()

    assert calls["path"] == str(settings.chroma_persist_dir)
    assert calls["deleted"] == settings.faq_collection_name
    assert calls["created"] == settings.faq_collection_name
    assert calls["collection_obj"] == {"name": settings.faq_collection_name}
    assert vector_store == {"vector_store": {"name": settings.faq_collection_name}}
    assert backend.resource_name == settings.faq_collection_name


@pytest.mark.unit
def test_chroma_vector_backend_load_query_vector_store_raises_unavailable(
    settings_factory,
    monkeypatch,
) -> None:
    settings = settings_factory()

    class FakeClient:
        def get_collection(self, *, name: str):
            raise RuntimeError(f"missing {name}")

    monkeypatch.setattr(
        "customer_bot.retrieval.backend.chromadb.PersistentClient",
        lambda path: FakeClient(),
    )

    backend = ChromaVectorBackend(settings)

    with pytest.raises(
        VectorBackendUnavailableError,
        match="Vector store collection is unavailable. Run `uv run customer-bot-ingest` first.",
    ):
        backend.load_query_vector_store()
