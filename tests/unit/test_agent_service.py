from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest
from llama_index.core.agent.workflow.workflow_events import AgentOutput
from llama_index.core.base.llms.types import ChatMessage

from customer_bot.agent.service import AgentService
from customer_bot.retrieval.types import RetrievalResult


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
        RetrievalResult(answer="Klicke auf Registrieren.", faq_id="faq_1", score=0.9)
    )
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    tool = service._build_tool()

    assert inspect.iscoroutinefunction(tool._real_fn)

    output = asyncio.run(tool.acall(question="Wie registriere ich mich?"))

    assert output.raw_output == "Klicke auf Registrieren."
    assert retriever.queries == ["Wie registriere ich mich?"]


@pytest.mark.unit
def test_collect_thinking_from_agent_output_event(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    retriever = FakeRetriever(RetrievalResult(answer=None, faq_id=None, score=None))
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(role="assistant", content="Antwort"),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich suche in den FAQ."}},
    )
    handler = FakeHandler(events=[event], result=event)

    thinking = asyncio.run(service._collect_thinking_from_events(handler))

    assert thinking == "Ich suche in den FAQ."


@pytest.mark.unit
def test_answer_sets_trace_output_and_keeps_fallback(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    retriever = FakeRetriever(RetrievalResult(answer=None, faq_id=None, score=None))
    service = AgentService(settings=settings, retriever=retriever, llm=object())  # type: ignore[arg-type]

    event = AgentOutput(
        response=ChatMessage(role="assistant", content=""),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich konnte keinen Treffer finden."}},
    )
    handler = FakeHandler(events=[event], result=event)

    class FakeFunctionAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def run(self, *args: Any, **kwargs: Any) -> FakeHandler:
            return handler

    observation = FakeObservation()
    langfuse_client = FakeLangfuseClient(observation=observation)

    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", FakeFunctionAgent)
    monkeypatch.setattr("customer_bot.agent.service.get_client", lambda: langfuse_client)

    answer = asyncio.run(
        service.answer(
            user_message="Unbekannte Frage",
            chat_history=[],
            session_id="session-42",
        )
    )

    assert answer == settings.fallback_text
    assert langfuse_client.calls[0]["input"] == {
        "user_message": "Unbekannte Frage",
        "session_id": "session-42",
    }
    assert observation.updates[-1]["output"] == {
        "answer": settings.fallback_text,
        "thinking": "Ich konnte keinen Treffer finden.",
    }
