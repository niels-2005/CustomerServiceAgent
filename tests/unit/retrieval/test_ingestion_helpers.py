from __future__ import annotations

from pathlib import Path

import pytest

from customer_bot.retrieval.ingestion import (
    CorpusValidationError,
    _render_price,
    load_corpus_records,
    load_product_records,
    render_product_ingestion_text,
)
from customer_bot.retrieval.types import ProductRecord


@pytest.mark.unit
def test_load_corpus_records_errors_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CorpusValidationError, match="Corpus file does not exist"):
        load_corpus_records(tmp_path / "missing.csv")


@pytest.mark.unit
def test_load_product_records_errors_for_empty_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text("product_id,name,description\n", encoding="utf-8")

    with pytest.raises(CorpusValidationError, match="Corpus CSV has no product rows."):
        load_product_records(csv_path)


@pytest.mark.unit
def test_render_price_tolerates_missing_pieces() -> None:
    assert _render_price("14.99", "EUR") == "14.99 EUR"
    assert _render_price("14.99", "") == "14.99"
    assert _render_price("", "EUR") == "EUR"


@pytest.mark.unit
def test_render_product_ingestion_text_skips_empty_optional_fields() -> None:
    record = ProductRecord(
        product_id="p1",
        name="Becher",
        description="Haelt warm.",
        category="",
        price="",
        currency="",
        availability="",
        features="",
        url="",
    )

    rendered = render_product_ingestion_text(record)

    assert rendered == "Produkt: Becher\nBeschreibung: Haelt warm."
