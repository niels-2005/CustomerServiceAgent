from __future__ import annotations

import asyncio
import inspect
import json

import pytest

from customer_bot.agent.tooling import FaqLookupInput, build_faq_tool
from customer_bot.retrieval.types import RetrievalHit, RetrievalResult
from tests.unit.agent_fakes import FakeRetriever


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
        description=settings.faq_tool_description,
    )

    assert inspect.iscoroutinefunction(tool._real_fn)
    assert tool.metadata.description == settings.faq_tool_description
    assert tool.metadata.fn_schema is FaqLookupInput
    assert tool.metadata.return_direct is False

    output = asyncio.run(tool.acall(question="Wie registriere ich mich?"))
    payload = json.loads(str(output.raw_output))

    assert payload["matches"] == [
        {"faq_id": "faq_1", "answer": "Klicke auf Registrieren.", "score": 0.9}
    ]
    assert retriever.queries == ["Wie registriere ich mich?"]
