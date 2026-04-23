from __future__ import annotations

import pytest
from pydantic import ValidationError

from customer_bot.config import Settings
from customer_bot.retrieval.ingestion import render_ingestion_text, render_product_ingestion_text
from customer_bot.retrieval.types import FaqRecord, ProductRecord


@pytest.mark.unit
def test_render_ingestion_text_question_only() -> None:
    record = FaqRecord(faq_id="faq_1", question="Frage", answer="Antwort")

    rendered = render_ingestion_text(record, "question_only")

    assert rendered == "Frage"


@pytest.mark.unit
def test_render_ingestion_text_answer_only() -> None:
    record = FaqRecord(faq_id="faq_1", question="Frage", answer="Antwort")

    rendered = render_ingestion_text(record, "answer_only")

    assert rendered == "Antwort"


@pytest.mark.unit
def test_render_ingestion_text_question_answer() -> None:
    record = FaqRecord(faq_id="faq_1", question="Frage", answer="Antwort")

    rendered = render_ingestion_text(record, "question_answer")

    assert rendered == "Frage: Frage\nAntwort: Antwort"


@pytest.mark.unit
def test_settings_rejects_invalid_text_ingestion_mode() -> None:
    with pytest.raises(ValidationError, match="faq_text_ingestion_mode"):
        Settings(faq_text_ingestion_mode="invalid_mode")


@pytest.mark.unit
def test_render_product_ingestion_text() -> None:
    record = ProductRecord(
        product_id="prod_1",
        name="Becher",
        description="Haelt warm.",
        category="lifestyle",
        price="14.99",
        currency="EUR",
        availability="available",
        features="Isoliert|Stylisch",
        url="https://example.com/becher",
    )

    rendered = render_product_ingestion_text(record)

    assert rendered == (
        "Produkt: Becher\n"
        "Beschreibung: Haelt warm.\n"
        "Kategorie: lifestyle\n"
        "Preis: 14.99 EUR\n"
        "Verfuegbarkeit: available\n"
        "Features: Isoliert, Stylisch\n"
        "URL: https://example.com/becher"
    )
