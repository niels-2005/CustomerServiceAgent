from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode

from customer_bot.config import Settings, TextIngestionMode
from customer_bot.llama import create_embedding_model
from customer_bot.retrieval.backend import ChromaVectorBackend, VectorStoreBackend
from customer_bot.retrieval.types import FaqRecord

REQUIRED_COLUMNS = ("faq_id", "question", "answer")


class CorpusValidationError(ValueError):
    """Raised when corpus input violates the expected contract."""


@dataclass(slots=True)
class IngestResult:
    records_ingested: int
    collection_name: str


def render_ingestion_text(record: FaqRecord, mode: TextIngestionMode) -> str:
    if mode == "question_only":
        return record.question
    if mode == "answer_only":
        return record.answer
    if mode == "question_answer":
        return f"Frage: {record.question}\nAntwort: {record.answer}"
    raise ValueError(f"Unsupported text ingestion mode: {mode}")


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
    def __init__(
        self,
        settings: Settings,
        embed_model: BaseEmbedding | None = None,
        vector_backend: VectorStoreBackend | None = None,
    ) -> None:
        self._settings = settings
        self._embed_model = embed_model or create_embedding_model(settings)
        self._vector_backend = vector_backend or ChromaVectorBackend(settings)

    def ingest(self, corpus_path: Path | None = None) -> IngestResult:
        target_path = corpus_path or self._settings.corpus_csv_path
        records = load_corpus_records(target_path)

        vector_store = self._vector_backend.build_ingestion_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        nodes = [
            TextNode(
                text=render_ingestion_text(record, self._settings.text_ingestion_mode),
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
            collection_name=self._vector_backend.resource_name,
        )
