from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore

from customer_bot.config import Settings
from customer_bot.llama import create_embedding_model
from customer_bot.retrieval.types import FaqRecord

REQUIRED_COLUMNS = ("faq_id", "question", "answer")


class CorpusValidationError(ValueError):
    """Raised when corpus input violates the expected contract."""


@dataclass(slots=True)
class IngestResult:
    records_ingested: int
    collection_name: str


def load_corpus_records(corpus_path: Path) -> list[FaqRecord]:
    if not corpus_path.exists():
        raise CorpusValidationError(f"Corpus file does not exist: {corpus_path}")

    with corpus_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CorpusValidationError("Corpus CSV is missing a header row.")

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise CorpusValidationError(f"Missing required CSV columns: {missing}")

        seen_ids: set[str] = set()
        records: list[FaqRecord] = []

        for row_number, row in enumerate(reader, start=2):
            faq_id = (row.get("faq_id") or "").strip()
            question = (row.get("question") or "").strip()
            answer = (row.get("answer") or "").strip()

            if not faq_id or not question or not answer:
                raise CorpusValidationError(
                    f"Invalid row {row_number}: faq_id, question, and answer are required."
                )

            if faq_id in seen_ids:
                raise CorpusValidationError(
                    f"Duplicate faq_id '{faq_id}' detected at row {row_number}."
                )

            seen_ids.add(faq_id)
            records.append(FaqRecord(faq_id=faq_id, question=question, answer=answer))

    if not records:
        raise CorpusValidationError("Corpus CSV has no FAQ rows.")

    return records


class IngestionService:
    def __init__(self, settings: Settings, embed_model: BaseEmbedding | None = None) -> None:
        self._settings = settings
        self._embed_model = embed_model or create_embedding_model(settings)

    def ingest(self, corpus_path: Path | None = None) -> IngestResult:
        target_path = corpus_path or self._settings.corpus_csv_path
        records = load_corpus_records(target_path)

        persist_path = str(self._settings.chroma_persist_dir)
        client = chromadb.PersistentClient(path=persist_path)

        try:
            client.delete_collection(name=self._settings.chroma_collection_name)
        except Exception:
            # A missing collection is fine for a first run.
            pass

        collection = client.get_or_create_collection(name=self._settings.chroma_collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        nodes = [
            TextNode(
                text=f"Frage: {record.question}\nAntwort: {record.answer}",
                metadata={
                    "faq_id": record.faq_id,
                    "question": record.question,
                    "answer": record.answer,
                },
            )
            for record in records
        ]

        VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            embed_model=self._embed_model,
            show_progress=False,
        )

        return IngestResult(
            records_ingested=len(records),
            collection_name=self._settings.chroma_collection_name,
        )
