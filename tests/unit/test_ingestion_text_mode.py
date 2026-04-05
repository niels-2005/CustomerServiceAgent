from __future__ import annotations

import pytest
from pydantic import ValidationError

from customer_bot.config import Settings
from customer_bot.retrieval.ingestion import render_ingestion_text
from customer_bot.retrieval.types import FaqRecord


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
    with pytest.raises(ValidationError, match="text_ingestion_mode"):
        Settings(text_ingestion_mode="invalid_mode")
