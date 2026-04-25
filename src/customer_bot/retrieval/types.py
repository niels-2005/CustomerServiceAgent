"""Typed retrieval records exchanged between ingestion, retrieval, and tools."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FaqRecord:
    """Validated FAQ corpus row used during ingestion."""

    faq_id: str
    question: str
    answer: str


@dataclass(slots=True)
class RetrievalHit:
    """One FAQ retrieval hit exposed to the agent/tooling layer."""

    faq_id: str
    answer: str
    score: float | None


@dataclass(slots=True)
class RetrievalResult:
    """Collection of FAQ retrieval hits ordered by retrieval score."""

    hits: list[RetrievalHit] = field(default_factory=list)


@dataclass(slots=True)
class ProductRecord:
    """Validated product corpus row used during ingestion."""

    product_id: str
    name: str
    description: str
    category: str = ""
    price: str = ""
    currency: str = ""
    availability: str = ""
    features: str = ""
    url: str = ""


@dataclass(slots=True)
class ProductRetrievalHit:
    """One product retrieval hit exposed to the agent/tooling layer."""

    product_id: str
    name: str
    description: str
    category: str
    price: str
    currency: str
    availability: str
    features: str
    url: str
    score: float | None


@dataclass(slots=True)
class ProductRetrievalResult:
    """Collection of product retrieval hits ordered by retrieval score."""

    hits: list[ProductRetrievalHit] = field(default_factory=list)
