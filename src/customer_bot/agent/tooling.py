from __future__ import annotations

import asyncio

from llama_index.core.tools import FunctionTool
from pydantic import BaseModel, Field

from customer_bot.retrieval.service import FaqRetrieverService
from customer_bot.retrieval.types import RetrievalHit

FAQ_TOOL_NAME = "faq_lookup"


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


def _to_lookup_match(hit: RetrievalHit) -> FaqLookupMatch:
    return FaqLookupMatch(faq_id=hit.faq_id, answer=hit.answer, score=hit.score)
