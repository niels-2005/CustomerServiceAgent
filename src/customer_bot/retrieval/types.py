from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FaqRecord:
    faq_id: str
    question: str
    answer: str


@dataclass(slots=True)
class RetrievalResult:
    answer: str | None
    faq_id: str | None
    score: float | None
