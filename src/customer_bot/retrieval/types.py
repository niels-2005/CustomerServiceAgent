"""Typed retrieval records exchanged between ingestion, retrieval, tools, and prefetch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


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


PrefetchSource = Literal["faq", "products"]


@dataclass(slots=True)
class RetrievalPrefetchContext:
    """Deterministic retrieval context prepared before agent execution.

    The context is request-local and advisory: it gives the agent grounded FAQ
    and product matches up front, but does not replace later tool calls when
    the prefetch result is empty, ambiguous, or insufficient.
    """

    query: str
    faq_hits: list[RetrievalHit] = field(default_factory=list)
    product_hits: list[ProductRetrievalHit] = field(default_factory=list)
    failed_sources: list[PrefetchSource] = field(default_factory=list)

    @property
    def has_hits(self) -> bool:
        """Return whether any deterministic match was found."""
        return bool(self.faq_hits or self.product_hits)

    @property
    def sources(self) -> list[PrefetchSource]:
        """Return the retrieval sources that produced at least one hit."""
        sources: list[PrefetchSource] = []
        if self.faq_hits:
            sources.append("faq")
        if self.product_hits:
            sources.append("products")
        return sources
