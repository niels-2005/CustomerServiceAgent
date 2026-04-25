"""Corpus validation and deterministic vector-store ingestion logic."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode

from customer_bot.config import Settings, TextIngestionMode
from customer_bot.model_factory import create_embedding_model
from customer_bot.retrieval.backend import ChromaVectorBackend, VectorStoreBackend
from customer_bot.retrieval.types import FaqRecord, ProductRecord

FAQ_REQUIRED_COLUMNS = ("faq_id", "question", "answer")
PRODUCT_REQUIRED_COLUMNS = ("product_id", "name", "description")
ProductIngestionSource = Literal["faq", "products"]


class CorpusValidationError(ValueError):
    """Raised when corpus input violates the expected contract."""


@dataclass(slots=True)
class IngestResult:
    """Summary returned after one ingestion run."""

    records_ingested: int
    collection_name: str


def render_ingestion_text(record: FaqRecord, mode: TextIngestionMode) -> str:
    """Render FAQ text exactly as it will be embedded for retrieval."""
    if mode == "question_only":
        return record.question
    if mode == "answer_only":
        return record.answer
    if mode == "question_answer":
        return f"Frage: {record.question}\nAntwort: {record.answer}"
    raise ValueError(f"Unsupported text ingestion mode: {mode}")


def render_product_ingestion_text(record: ProductRecord) -> str:
    """Render product metadata into the text stored for product retrieval."""
    lines = [
        f"Produkt: {record.name}",
        f"Beschreibung: {record.description}",
    ]
    optional_fields = (
        ("Kategorie", record.category),
        ("Preis", _render_price(record.price, record.currency)),
        ("Verfuegbarkeit", record.availability),
        ("Features", record.features.replace("|", ", ")),
        ("URL", record.url),
    )
    for label, value in optional_fields:
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _render_price(price: str, currency: str) -> str:
    """Join price and currency while tolerating missing pieces."""
    if price and currency:
        return f"{price} {currency}"
    return price or currency


def load_corpus_records(corpus_path: Path) -> list[FaqRecord]:
    """Load and validate FAQ corpus rows from CSV."""
    if not corpus_path.exists():
        raise CorpusValidationError(f"Corpus file does not exist: {corpus_path}")

    with corpus_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CorpusValidationError("Corpus CSV is missing a header row.")

        missing_columns = [
            column for column in FAQ_REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
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


def load_product_records(corpus_path: Path) -> list[ProductRecord]:
    """Load and validate product corpus rows from CSV."""
    if not corpus_path.exists():
        raise CorpusValidationError(f"Corpus file does not exist: {corpus_path}")

    with corpus_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CorpusValidationError("Corpus CSV is missing a header row.")

        missing_columns = [
            column for column in PRODUCT_REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise CorpusValidationError(f"Missing required CSV columns: {missing}")

        seen_ids: set[str] = set()
        records: list[ProductRecord] = []

        for row_number, row in enumerate(reader, start=2):
            product_id = (row.get("product_id") or "").strip()
            name = (row.get("name") or "").strip()
            description = (row.get("description") or "").strip()
            category = (row.get("category") or "").strip()
            price = (row.get("price") or "").strip()
            currency = (row.get("currency") or "").strip()
            availability = (row.get("availability") or "").strip()
            features = (row.get("features") or "").strip()
            url = (row.get("url") or "").strip()

            if not product_id or not name or not description:
                raise CorpusValidationError(
                    f"Invalid row {row_number}: product_id, name, and description are required."
                )

            if product_id in seen_ids:
                raise CorpusValidationError(
                    f"Duplicate product_id '{product_id}' detected at row {row_number}."
                )

            seen_ids.add(product_id)
            records.append(
                ProductRecord(
                    product_id=product_id,
                    name=name,
                    description=description,
                    category=category,
                    price=price,
                    currency=currency,
                    availability=availability,
                    features=features,
                    url=url,
                )
            )

    if not records:
        raise CorpusValidationError("Corpus CSV has no product rows.")

    return records


class IngestionService:
    """Build vector-store indexes from validated FAQ or product corpora."""

    def __init__(
        self,
        settings: Settings,
        embed_model: BaseEmbedding | None = None,
        vector_backend: VectorStoreBackend | None = None,
        product_vector_backend: VectorStoreBackend | None = None,
    ) -> None:
        self._settings = settings
        self._embed_model = embed_model or create_embedding_model(settings)
        self._faq_vector_backend = vector_backend or ChromaVectorBackend(settings)
        self._product_vector_backend = product_vector_backend or ChromaVectorBackend(
            settings,
            collection_name=settings.storage.products.collection_name,
        )

    def ingest(
        self,
        source: ProductIngestionSource = "faq",
        corpus_path: Path | None = None,
    ) -> IngestResult:
        """Ingest the selected source into its target vector-store collection."""
        if source == "faq":
            target_path = corpus_path or self._settings.ingestion.faq.corpus_csv_path
            records = load_corpus_records(target_path)
            nodes = [
                TextNode(
                    text=render_ingestion_text(
                        record,
                        self._settings.ingestion.faq.text_ingestion_mode,
                    ),
                    metadata={
                        "faq_id": record.faq_id,
                        "question": record.question,
                        "answer": record.answer,
                    },
                )
                for record in records
            ]
            vector_backend = self._faq_vector_backend
        else:
            target_path = corpus_path or self._settings.ingestion.products.corpus_csv_path
            records = load_product_records(target_path)
            nodes = [
                TextNode(
                    text=render_product_ingestion_text(record),
                    metadata={
                        "product_id": record.product_id,
                        "name": record.name,
                        "description": record.description,
                        "category": record.category,
                        "price": record.price,
                        "currency": record.currency,
                        "availability": record.availability,
                        "features": record.features,
                        "url": record.url,
                    },
                )
                for record in records
            ]
            vector_backend = self._product_vector_backend

        vector_store = vector_backend.build_ingestion_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            embed_model=self._embed_model,
            show_progress=False,
        )

        return IngestResult(
            records_ingested=len(records),
            collection_name=vector_backend.resource_name,
        )
