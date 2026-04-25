"""Tool schemas and builders exposed to the LlamaIndex agent.

The tools wrap retrieval services behind stable JSON contracts so the agent can
query FAQs and product data without coupling itself to internal Python types.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from llama_index.core.tools import FunctionTool
from pydantic import BaseModel, Field

from customer_bot.retrieval.types import (
    ProductRetrievalHit,
    ProductRetrievalResult,
    RetrievalHit,
    RetrievalResult,
)

FAQ_TOOL_NAME = "faq_lookup"
PRODUCT_TOOL_NAME = "product_lookup"


class SupportsFaqRetrieval(Protocol):
    """Consumer-facing contract for FAQ lookup dependencies."""

    def retrieve_best_answer(self, query: str) -> RetrievalResult: ...


class SupportsProductRetrieval(Protocol):
    """Consumer-facing contract for product lookup dependencies."""

    def retrieve_products(self, query: str) -> ProductRetrievalResult: ...


class FaqLookupInput(BaseModel):
    """Input schema for the FAQ lookup tool."""

    question: str = Field(description="User question to look up in the FAQ corpus.")


class FaqLookupMatch(BaseModel):
    """One FAQ match returned to the agent."""

    faq_id: str = Field(description="FAQ identifier of a matched entry.")
    answer: str = Field(description="FAQ answer text for the matched entry.")
    score: float | None = Field(
        default=None,
        description="Similarity score of the matched entry, when available.",
    )


class FaqLookupOutput(BaseModel):
    """Serialized FAQ lookup payload returned to the agent."""

    matches: list[FaqLookupMatch] = Field(
        default_factory=list,
        description="Ranked FAQ matches after similarity filtering.",
    )


class ProductLookupInput(BaseModel):
    """Input schema for the product lookup tool."""

    query: str = Field(description="User request to look up product information.")


class ProductLookupMatch(BaseModel):
    """One product match returned to the agent."""

    product_id: str = Field(description="Product identifier of a matched entry.")
    name: str = Field(description="Product name.")
    description: str = Field(description="Product description text.")
    category: str = Field(default="", description="Product category.")
    price: str = Field(default="", description="Product price value.")
    currency: str = Field(default="", description="Currency code for the price.")
    availability: str = Field(default="", description="Availability status.")
    features: str = Field(default="", description="Delimited product feature summary.")
    url: str = Field(default="", description="Product URL when available.")
    score: float | None = Field(
        default=None,
        description="Similarity score of the matched entry, when available.",
    )


class ProductLookupOutput(BaseModel):
    """Serialized product lookup payload returned to the agent."""

    matches: list[ProductLookupMatch] = Field(
        default_factory=list,
        description="Ranked product matches after similarity filtering.",
    )


def build_faq_tool(retriever: SupportsFaqRetrieval, description: str) -> FunctionTool:
    """Build the FAQ retrieval tool exposed to the agent."""

    async def faq_lookup(question: str) -> str:
        # Retrieval remains synchronous, so the tool delegates it to a worker
        # thread to avoid blocking the async agent runtime.
        retrieval_result = await asyncio.to_thread(retriever.retrieve_best_answer, question)
        payload = FaqLookupOutput(matches=[_to_lookup_match(hit) for hit in retrieval_result.hits])
        return payload.model_dump_json(ensure_ascii=False)

    return FunctionTool.from_defaults(
        async_fn=faq_lookup,
        name=FAQ_TOOL_NAME,
        description=description,
        return_direct=False,
        fn_schema=FaqLookupInput,
    )


def build_product_tool(retriever: SupportsProductRetrieval, description: str) -> FunctionTool:
    """Build the product retrieval tool exposed to the agent."""

    async def product_lookup(query: str) -> str:
        retrieval_result = await asyncio.to_thread(retriever.retrieve_products, query)
        payload = ProductLookupOutput(
            matches=[_to_product_lookup_match(hit) for hit in retrieval_result.hits]
        )
        return payload.model_dump_json(ensure_ascii=False)

    return FunctionTool.from_defaults(
        async_fn=product_lookup,
        name=PRODUCT_TOOL_NAME,
        description=description,
        return_direct=False,
        fn_schema=ProductLookupInput,
    )


def _to_lookup_match(hit: RetrievalHit) -> FaqLookupMatch:
    """Convert one internal FAQ retrieval hit into the tool schema."""
    return FaqLookupMatch(faq_id=hit.faq_id, answer=hit.answer, score=hit.score)


def _to_product_lookup_match(hit: ProductRetrievalHit) -> ProductLookupMatch:
    """Convert one internal product retrieval hit into the tool schema."""
    return ProductLookupMatch(
        product_id=hit.product_id,
        name=hit.name,
        description=hit.description,
        category=hit.category,
        price=hit.price,
        currency=hit.currency,
        availability=hit.availability,
        features=hit.features,
        url=hit.url,
        score=hit.score,
    )
