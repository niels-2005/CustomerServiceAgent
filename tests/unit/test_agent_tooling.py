from __future__ import annotations

import asyncio
import inspect
import json

import pytest

from customer_bot.agent.tooling import (
    FaqLookupInput,
    ProductLookupInput,
    build_faq_tool,
    build_product_tool,
)
from customer_bot.retrieval.types import (
    ProductRetrievalHit,
    ProductRetrievalResult,
    RetrievalHit,
    RetrievalResult,
)
from tests.unit.agent_fakes import FakeProductRetriever, FakeRetriever


@pytest.mark.unit
def test_build_tool_uses_async_retrieval(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(
        RetrievalResult(
            hits=[RetrievalHit(faq_id="faq_1", answer="Klicke auf Registrieren.", score=0.9)]
        )
    )

    tool = build_faq_tool(
        retriever=retriever,
        description=settings.messages.faq_tool_description,
    )

    assert inspect.iscoroutinefunction(tool._real_fn)
    assert tool.metadata.description == settings.messages.faq_tool_description
    assert tool.metadata.fn_schema is FaqLookupInput
    assert tool.metadata.return_direct is False

    output = asyncio.run(tool.acall(question="Wie registriere ich mich?"))
    payload = json.loads(str(output.raw_output))

    assert payload["matches"] == [
        {"faq_id": "faq_1", "answer": "Klicke auf Registrieren.", "score": 0.9}
    ]
    assert retriever.queries == ["Wie registriere ich mich?"]


@pytest.mark.unit
def test_build_product_tool_uses_async_retrieval(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeProductRetriever(
        ProductRetrievalResult(
            hits=[
                ProductRetrievalHit(
                    product_id="prod_1",
                    name="NexaCup Thermal Mug",
                    description="Haelt Kaffee warm.",
                    category="lifestyle",
                    price="14.99",
                    currency="EUR",
                    availability="available",
                    features="Isoliert|Stylisch",
                    url="https://example.com/mug",
                    score=0.91,
                )
            ]
        )
    )

    tool = build_product_tool(
        retriever=retriever,
        description=settings.messages.product_tool_description,
    )

    assert inspect.iscoroutinefunction(tool._real_fn)
    assert tool.metadata.description == settings.messages.product_tool_description
    assert tool.metadata.fn_schema is ProductLookupInput
    assert tool.metadata.return_direct is False

    output = asyncio.run(tool.acall(query="Erzaehl mir etwas ueber den Becher"))
    payload = json.loads(str(output.raw_output))

    assert payload["matches"] == [
        {
            "product_id": "prod_1",
            "name": "NexaCup Thermal Mug",
            "description": "Haelt Kaffee warm.",
            "category": "lifestyle",
            "price": "14.99",
            "currency": "EUR",
            "availability": "available",
            "features": "Isoliert|Stylisch",
            "url": "https://example.com/mug",
            "score": 0.91,
        }
    ]
    assert retriever.queries == ["Erzaehl mir etwas ueber den Becher"]
