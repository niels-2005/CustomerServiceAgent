from __future__ import annotations

import asyncio
from typing import Any

import pytest
from llama_index.core.agent.workflow.workflow_events import AgentOutput, ToolCallResult
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools.types import ToolOutput

from customer_bot.agent.service import AgentService
from customer_bot.agent.tooling import FaqLookupInput, ProductLookupInput
from customer_bot.retrieval.types import ProductRetrievalResult, RetrievalHit, RetrievalResult
from tests.unit.agent_fakes import (
    FakeHandler,
    FakeLangfuseClient,
    FakeObservation,
    FakeProductRetriever,
    FakeRetriever,
    FakeSessionContext,
)


@pytest.mark.unit
def test_answer_builds_function_agent_from_settings(monkeypatch, settings_factory) -> None:
    settings = settings_factory(
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
        agent_description="Configured FAQ agent description.",
        agent_system_prompt="Configured FAQ system prompt.",
        no_match_instruction="Configured no-match instruction.",
        faq_tool_description="Configured FAQ tool description.",
        agent_timeout_seconds=12.5,
    )
    retriever = FakeRetriever(
        RetrievalResult(hits=[RetrievalHit(answer="Antwort", faq_id="faq_1", score=0.9)])
    )
    product_retriever = FakeProductRetriever(ProductRetrievalResult())
    service = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=object(),
    )  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(role="assistant", content="Antwort"),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Gedanke"}},
    )
    handler = FakeHandler(events=[event], result=event)
    captured: dict[str, Any] = {}

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured["kwargs"] = kwargs

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)

    result = asyncio.run(
        service.answer(
            user_message="Hallo",
            chat_history=[],
            session_id="session-config",
        )
    )

    assert result.answer == "Antwort"
    assert captured["kwargs"]["description"] == settings.agent_description
    assert captured["kwargs"]["system_prompt"] == (
        "Configured FAQ system prompt.\n\n"
        "FAQ no-match guidance: Configured no-match instruction.\n\n"
        f"Product no-match guidance: {settings.product_no_match_instruction}"
    )
    assert captured["kwargs"]["timeout"] == settings.agent_timeout_seconds
    assert len(captured["kwargs"]["tools"]) == 2
    faq_tool = captured["kwargs"]["tools"][0]
    product_tool = captured["kwargs"]["tools"][1]
    assert faq_tool.metadata.description == settings.faq_tool_description
    assert faq_tool.metadata.fn_schema is FaqLookupInput
    assert faq_tool.metadata.return_direct is False
    assert product_tool.metadata.description == settings.product_tool_description
    assert product_tool.metadata.fn_schema is ProductLookupInput
    assert product_tool.metadata.return_direct is False


@pytest.mark.unit
def test_answer_uses_error_fallback_for_empty_model_response(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    retriever = FakeRetriever(RetrievalResult())
    product_retriever = FakeProductRetriever(ProductRetrievalResult())
    service = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=object(),
    )  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(role="assistant", content=""),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich konnte keinen Treffer finden."}},
    )
    tool_event = ToolCallResult(
        tool_name="faq_lookup",
        tool_kwargs={"question": "Unbekannte Frage"},
        tool_id="tool-2",
        tool_output=ToolOutput(
            tool_name="faq_lookup",
            content="",
            raw_input={},
            raw_output={"matches": []},
            is_error=False,
        ),
        return_direct=False,
    )
    handler = FakeHandler(events=[event, tool_event], result=event)

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    observation = FakeObservation()
    langfuse_client = FakeLangfuseClient(observation=observation)
    session_calls: list[dict[str, Any]] = []

    def fake_propagate_attributes(**kwargs: Any) -> FakeSessionContext:
        session_calls.append(kwargs)
        return FakeSessionContext()

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr("customer_bot.agent.tracing.get_client", lambda: langfuse_client)
    monkeypatch.setattr(
        "customer_bot.agent.tracing.propagate_attributes",
        fake_propagate_attributes,
    )

    result = asyncio.run(
        service.answer(
            user_message="Unbekannte Frage",
            chat_history=[],
            session_id="session-42",
        )
    )

    assert result.answer == settings.error_fallback_text
    assert session_calls == [
        {
            "session_id": "session-42",
            "trace_name": "chat_request",
            "tags": ["chat", "faq-agent"],
        }
    ]
    assert observation.updates[-1]["output"] == {"answer": settings.error_fallback_text}
    assert observation.updates[-1]["metadata"] == {
        "system_prompt_version": "v1",
        "tool_count": 1,
        "tool_question": "Unbekannte Frage",
        "tool_error": False,
        "no_match": True,
        "thinking": {
            "steps": ["Ich konnte keinen Treffer finden."],
            "full_text": "Ich konnte keinen Treffer finden.",
        },
    }
    assert observation.updates[-1]["level"] == "WARNING"
    assert observation.updates[-1]["status_message"] == "No knowledge match found."


@pytest.mark.unit
def test_answer_keeps_agent_written_no_match_response(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    product_retriever = FakeProductRetriever(ProductRetrievalResult())
    service = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=object(),
    )  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(
            role="assistant",
            content=(
                "Ich habe dazu in den FAQs aktuell keine verlässliche Information gefunden. "
                "Bitte kontaktiere den Support direkt."
            ),
        ),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich formuliere eine No-Match-Antwort."}},
    )
    tool_event = ToolCallResult(
        tool_name="faq_lookup",
        tool_kwargs={"question": "Unbekannte Frage"},
        tool_id="tool-no-match",
        tool_output=ToolOutput(
            tool_name="faq_lookup",
            content="",
            raw_input={},
            raw_output={"matches": []},
            is_error=False,
        ),
        return_direct=False,
    )
    handler = FakeHandler(events=[event, tool_event], result=event)

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)

    result = asyncio.run(
        service.answer(
            user_message="Unbekannte Frage",
            chat_history=[],
            session_id="session-no-match",
        )
    )

    assert result.answer == (
        "Ich habe dazu in den FAQs aktuell keine verlässliche Information gefunden. "
        "Bitte kontaktiere den Support direkt."
    )


@pytest.mark.unit
def test_answer_without_tool_call_does_not_force_fallback(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    product_retriever = FakeProductRetriever(ProductRetrievalResult())
    service = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=object(),
    )  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(
            role="assistant", content="Wie oben beschrieben gilt der gleiche Ablauf."
        ),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich beantworte die Follow-up-Frage aus dem Verlauf."}},
    )
    handler = FakeHandler(events=[event], result=event)

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)

    result = asyncio.run(
        service.answer(
            user_message="Und wie ist das dann beim Passwort?",
            chat_history=[ChatMessage(role="assistant", content="Vorherige FAQ-Antwort")],
            session_id="session-follow-up",
        )
    )

    assert result.answer == "Wie oben beschrieben gilt der gleiche Ablauf."
    assert result.used_history_only is True


@pytest.mark.unit
def test_answer_uses_error_fallback_for_tool_errors(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    retriever = FakeRetriever(RetrievalResult())
    product_retriever = FakeProductRetriever(ProductRetrievalResult())
    service = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=object(),
    )  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(role="assistant", content="Ich habe eine Antwort."),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich habe ein Tool-Problem gesehen."}},
    )
    tool_event = ToolCallResult(
        tool_name="faq_lookup",
        tool_kwargs={"question": "Frage"},
        tool_id="tool-error",
        tool_output=ToolOutput(
            tool_name="faq_lookup",
            content="",
            raw_input={},
            raw_output={"detail": "timeout"},
            is_error=True,
        ),
        return_direct=False,
    )
    handler = FakeHandler(events=[event, tool_event], result=event)

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    observation = FakeObservation()
    langfuse_client = FakeLangfuseClient(observation=observation)

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr("customer_bot.agent.tracing.get_client", lambda: langfuse_client)
    monkeypatch.setattr(
        "customer_bot.agent.tracing.propagate_attributes",
        lambda **kwargs: FakeSessionContext(),
    )

    result = asyncio.run(
        service.answer(
            user_message="Frage",
            chat_history=[],
            session_id="session-tool-error",
        )
    )

    assert result.answer == settings.error_fallback_text
    assert observation.updates[-1]["output"] == {"answer": settings.error_fallback_text}
    assert observation.updates[-1]["metadata"] == {
        "system_prompt_version": "v1",
        "tool_count": 1,
        "tool_question": "Frage",
        "tool_error": True,
        "no_match": False,
        "thinking": {
            "steps": ["Ich habe ein Tool-Problem gesehen."],
            "full_text": "Ich habe ein Tool-Problem gesehen.",
        },
    }
    assert observation.updates[-1]["level"] == "ERROR"
    assert observation.updates[-1]["status_message"] == (
        "Tool or agent execution failed; technical fallback returned."
    )


@pytest.mark.unit
def test_answer_uses_error_fallback_when_agent_raises(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    product_retriever = FakeProductRetriever(ProductRetrievalResult())
    service = AgentService(
        settings=settings,
        retriever=retriever,
        product_retriever=product_retriever,
        llm=object(),
    )  # type: ignore[arg-type]

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            raise RuntimeError("boom")

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)

    result = asyncio.run(
        service.answer(
            user_message="Hallo",
            chat_history=[],
            session_id="session-error",
        )
    )

    assert result.answer == settings.error_fallback_text
