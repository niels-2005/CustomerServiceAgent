from __future__ import annotations

from pathlib import Path

import pytest

from customer_bot.retrieval.ingestion import (
    CorpusValidationError,
    load_corpus_records,
    load_product_records,
)


@pytest.mark.unit
def test_load_corpus_records_valid(tmp_path: Path) -> None:
    csv_path = tmp_path / "corpus.csv"
    csv_path.write_text(
        "faq_id,question,answer\nfaq_1,Wie geht Login?,Nutze den Login Button.\n",
        encoding="utf-8",
    )

    records = load_corpus_records(csv_path)

    assert len(records) == 1
    assert records[0].faq_id == "faq_1"


@pytest.mark.unit
def test_load_corpus_records_missing_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "corpus.csv"
    csv_path.write_text("faq_id,question\nfaq_1,Frage\n", encoding="utf-8")

    with pytest.raises(CorpusValidationError, match="Missing required CSV columns"):
        load_corpus_records(csv_path)


@pytest.mark.unit
def test_load_corpus_records_duplicate_faq_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "corpus.csv"
    csv_path.write_text(
        "faq_id,question,answer\nfaq_1,Frage 1,Antwort 1\nfaq_1,Frage 2,Antwort 2\n",
        encoding="utf-8",
    )

    with pytest.raises(CorpusValidationError, match="Duplicate faq_id"):
        load_corpus_records(csv_path)


@pytest.mark.unit
def test_load_product_records_valid(tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "product_id,name,description,category\nprod_1,Becher,Haelt warm,lifestyle\n",
        encoding="utf-8",
    )

    records = load_product_records(csv_path)

    assert len(records) == 1
    assert records[0].product_id == "prod_1"


@pytest.mark.unit
def test_load_product_records_missing_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text("product_id,name\nprod_1,Becher\n", encoding="utf-8")

    with pytest.raises(CorpusValidationError, match="Missing required CSV columns"):
        load_product_records(csv_path)


@pytest.mark.unit
def test_load_product_records_duplicate_product_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "product_id,name,description\nprod_1,Becher,A\nprod_1,Tasse,B\n",
        encoding="utf-8",
    )

    with pytest.raises(CorpusValidationError, match="Duplicate product_id"):
        load_product_records(csv_path)
