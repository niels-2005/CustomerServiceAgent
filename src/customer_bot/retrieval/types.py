from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FaqRecord:
    faq_id: str
    question: str
    answer: str


@dataclass(slots=True)
class RetrievalHit:
    faq_id: str
    answer: str
    score: float | None


@dataclass(slots=True)
class RetrievalResult:
    hits: list[RetrievalHit] = field(default_factory=list)


@dataclass(slots=True)
class ProductRecord:
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
    hits: list[ProductRetrievalHit] = field(default_factory=list)
