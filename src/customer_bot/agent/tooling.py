from __future__ import annotations

import asyncio

from llama_index.core.tools import FunctionTool
from pydantic import BaseModel, Field

from customer_bot.retrieval.service import FaqRetrieverService, ProductRetrieverService
from customer_bot.retrieval.types import ProductRetrievalHit, RetrievalHit

FAQ_TOOL_NAME = "faq_lookup"
PRODUCT_TOOL_NAME = "product_lookup"


class FaqLookupInput(BaseModel):
    question: str = Field(description="User question to look up in the FAQ corpus.")


class FaqLookupMatch(BaseModel):
    faq_id: str = Field(description="FAQ identifier of a matched entry.")
    answer: str = Field(description="FAQ answer text for the matched entry.")
    score: float | None = Field(
        default=None,
        description="Similarity score of the matched entry, when available.",
    )


class FaqLookupOutput(BaseModel):
    matches: list[FaqLookupMatch] = Field(
        default_factory=list,
        description="Ranked FAQ matches after similarity filtering.",
    )


class ProductLookupInput(BaseModel):
    query: str = Field(description="User request to look up product information.")


class ProductLookupMatch(BaseModel):
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
    matches: list[ProductLookupMatch] = Field(
        default_factory=list,
        description="Ranked product matches after similarity filtering.",
    )


def build_faq_tool(retriever: FaqRetrieverService, description: str) -> FunctionTool:
    async def faq_lookup(question: str) -> str:
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


def build_product_tool(retriever: ProductRetrieverService, description: str) -> FunctionTool:
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
    return FaqLookupMatch(faq_id=hit.faq_id, answer=hit.answer, score=hit.score)


def _to_product_lookup_match(hit: ProductRetrievalHit) -> ProductLookupMatch:
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
