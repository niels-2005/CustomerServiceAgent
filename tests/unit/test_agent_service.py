from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import pytest
from llama_index.core.agent.workflow.workflow_events import AgentOutput, ToolCallResult
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools.types import ToolOutput

from customer_bot.agent.service import AgentService, FaqLookupInput
from customer_bot.retrieval.types import RetrievalHit, RetrievalResult


class FakeRetriever:
    def __init__(self, result: RetrievalResult) -> None:
        self._result = result
        self.queries: list[str] = []

    def retrieve_best_answer(self, query: str) -> RetrievalResult:
        self.queries.append(query)
        return self._result


class FakeHandler:
    def __init__(self, events: list[Any], result: AgentOutput) -> None:
        self._events = events
        self._result = result

    async def stream_events(self):
        for event in self._events:
            yield event

    async def _resolve(self) -> AgentOutput:
        return self._result

    def __await__(self):
        return self._resolve().__await__()


class FakeObservation:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)


class FakeObservationContext:
    def __init__(self, observation: FakeObservation) -> None:
        self._observation = observation

    def __enter__(self) -> FakeObservation:
        return self._observation

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeLangfuseClient:
    def __init__(self, observation: FakeObservation) -> None:
        self.observation = observation
        self.calls: list[dict[str, Any]] = []

    def start_as_current_observation(self, **kwargs: Any) -> FakeObservationContext:
        self.calls.append(kwargs)
        return FakeObservationContext(self.observation)


@pytest.mark.unit
def test_build_tool_uses_async_retrieval(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(
        RetrievalResult(
            hits=[RetrievalHit(faq_id="faq_1", answer="Klicke auf Registrieren.", score=0.9)]
        )
    )
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    tool = service._build_tool()

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
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

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

    answer = asyncio.run(
        service.answer(
            user_message="Hallo",
            chat_history=[],
            session_id="session-config",
        )
    )

    assert answer == "Antwort"
    assert captured["kwargs"]["description"] == settings.agent_description
    assert captured["kwargs"]["system_prompt"] == (
        "Configured FAQ system prompt.\n\nNo-match guidance: Configured no-match instruction."
    )
    assert captured["kwargs"]["timeout"] == settings.agent_timeout_seconds
    tool = captured["kwargs"]["tools"][0]
    assert tool.metadata.description == settings.faq_tool_description
    assert tool.metadata.fn_schema is FaqLookupInput
    assert tool.metadata.return_direct is False


@pytest.mark.unit
def test_collect_event_data_from_agent_and_tool_events(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    agent_event = AgentOutput(
        response=ChatMessage(role="assistant", content="Antwort"),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich suche in den FAQ."}},
    )
    tool_event = ToolCallResult(
        tool_name="faq_lookup",
        tool_kwargs={"question": "Wie registriere ich mich?"},
        tool_id="tool-1",
        tool_output=ToolOutput(
            tool_name="faq_lookup",
            content="Klicke auf Registrieren.",
            raw_input={},
            raw_output={"answer": "Klicke auf Registrieren."},
            is_error=False,
        ),
        return_direct=False,
    )
    handler = FakeHandler(events=[agent_event, tool_event], result=agent_event)

    thinking, tool_calls, has_tool_error = asyncio.run(service._collect_event_data(handler))

    assert thinking == "Ich suche in den FAQ."
    assert has_tool_error is False
    assert tool_calls == [
        {
            "tool_name": "faq_lookup",
            "tool_input": {"question": "Wie registriere ich mich?"},
            "tool_output": "Klicke auf Registrieren.",
            "is_error": False,
        }
    ]


@pytest.mark.unit
def test_answer_uses_error_fallback_for_empty_model_response(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    retriever = FakeRetriever(RetrievalResult())
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

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

    class FakeSessionContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_propagate_attributes(**kwargs: Any) -> FakeSessionContext:
        session_calls.append(kwargs)
        return FakeSessionContext()

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr("customer_bot.agent.service.get_client", lambda: langfuse_client)
    monkeypatch.setattr(
        "customer_bot.agent.service.propagate_attributes", fake_propagate_attributes
    )

    answer = asyncio.run(
        service.answer(
            user_message="Unbekannte Frage",
            chat_history=[],
            session_id="session-42",
        )
    )

    assert answer == settings.error_fallback_text
    assert langfuse_client.calls[0]["input"] == {
        "user_message": "Unbekannte Frage",
        "session_id": "session-42",
    }
    assert session_calls == [{"session_id": "session-42"}]
    assert observation.updates[-1]["output"] == {
        "answer": settings.error_fallback_text,
        "thinking": "Ich konnte keinen Treffer finden.",
        "tool_calls": [
            {
                "tool_name": "faq_lookup",
                "tool_input": {"question": "Unbekannte Frage"},
                "tool_output": {"matches": []},
                "is_error": False,
            }
        ],
    }


@pytest.mark.unit
def test_answer_keeps_agent_written_no_match_response(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

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

    answer = asyncio.run(
        service.answer(
            user_message="Unbekannte Frage",
            chat_history=[],
            session_id="session-no-match",
        )
    )

    assert answer == (
        "Ich habe dazu in den FAQs aktuell keine verlässliche Information gefunden. "
        "Bitte kontaktiere den Support direkt."
    )


@pytest.mark.unit
def test_answer_without_tool_call_does_not_force_fallback(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

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

    answer = asyncio.run(
        service.answer(
            user_message="Und wie ist das dann beim Passwort?",
            chat_history=[ChatMessage(role="assistant", content="Vorherige FAQ-Antwort")],
            session_id="session-follow-up",
        )
    )

    assert answer == "Wie oben beschrieben gilt der gleiche Ablauf."


@pytest.mark.unit
def test_answer_uses_error_fallback_for_tool_errors(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

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
            content="timeout",
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

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)

    answer = asyncio.run(
        service.answer(
            user_message="Frage",
            chat_history=[],
            session_id="session-tool-error",
        )
    )

    assert answer == settings.error_fallback_text


@pytest.mark.unit
def test_answer_uses_error_fallback_when_agent_raises(monkeypatch, settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult())
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            raise RuntimeError("boom")

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)

    answer = asyncio.run(
        service.answer(
            user_message="Hallo",
            chat_history=[],
            session_id="session-error",
        )
    )

    assert answer == settings.error_fallback_text


@pytest.mark.unit
def test_answer_without_langfuse_keys_skips_session_propagation(
    monkeypatch, settings_factory
) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(
        RetrievalResult(hits=[RetrievalHit(answer="Antwort", faq_id="faq_1", score=0.9)])
    )
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(role="assistant", content="Antwort"),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Gedanke"}},
    )
    handler = FakeHandler(events=[event], result=event)

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    session_calls: list[dict[str, Any]] = []

    def fake_propagate_attributes(**kwargs: Any):
        session_calls.append(kwargs)
        raise AssertionError("propagate_attributes should not be called when disabled")

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr(
        "customer_bot.agent.service.propagate_attributes", fake_propagate_attributes
    )

    answer = asyncio.run(
        service.answer(
            user_message="Hallo",
            chat_history=[],
            session_id="session-no-langfuse",
        )
    )

    assert answer == "Antwort"
    assert session_calls == []
