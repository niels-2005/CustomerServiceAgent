from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from llama_index.core.agent.workflow.workflow_events import AgentOutput, ToolCallResult
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools.types import ToolOutput

from customer_bot.agent.tracing import (
    LANGFUSE_SYSTEM_PROMPT_VERSION,
    LANGFUSE_TRACE_NAME,
    AgentTraceHelper,
    CollectedEventData,
)
from tests.unit.agent_fakes import (
    FakeHandler,
    FakeLangfuseClient,
    FakeObservation,
    FakeSessionContext,
)


@pytest.mark.unit
def test_collect_event_data_from_agent_and_tool_events(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)

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
            content=json.dumps(
                {
                    "matches": [
                        {
                            "faq_id": "faq_1",
                            "answer": "Klicke auf Registrieren.",
                            "score": 0.9,
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            raw_input={},
            raw_output={
                "matches": [
                    {
                        "faq_id": "faq_1",
                        "answer": "Klicke auf Registrieren.",
                        "score": 0.9,
                    }
                ]
            },
            is_error=False,
        ),
        return_direct=False,
    )
    handler = FakeHandler(events=[agent_event, tool_event], result=agent_event)

    collected = asyncio.run(helper.collect_event_data(handler))

    assert collected.thinking == "Ich suche in den FAQ."
    assert collected.has_tool_error is False
    assert collected.has_no_match is False
    assert collected.tool_calls == [
        {
            "tool_name": "faq_lookup",
            "tool_input": "Wie registriere ich mich?",
            "tool_output": "faq_1: Klicke auf Registrieren.",
            "is_error": False,
        }
    ]


@pytest.mark.unit
def test_collect_event_data_aggregates_thinking_across_tool_calls(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)

    first_thinking = AgentOutput(
        response=ChatMessage(role="assistant", content=""),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich suche in den FAQ."}},
    )
    duplicate_thinking = AgentOutput(
        response=ChatMessage(role="assistant", content=""),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich suche in den FAQ."}},
    )
    tool_event = ToolCallResult(
        tool_name="faq_lookup",
        tool_kwargs={"question": "Wie registriere ich mich?"},
        tool_id="tool-thinking",
        tool_output=ToolOutput(
            tool_name="faq_lookup",
            content="",
            raw_input={},
            raw_output={"matches": []},
            is_error=False,
        ),
        return_direct=False,
    )
    repeated_after_tool = AgentOutput(
        response=ChatMessage(role="assistant", content=""),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich suche in den FAQ."}},
    )
    final_thinking = AgentOutput(
        response=ChatMessage(role="assistant", content="Antwort"),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich formuliere die Antwort."}},
    )
    handler = FakeHandler(
        events=[
            first_thinking,
            duplicate_thinking,
            tool_event,
            repeated_after_tool,
            final_thinking,
        ],
        result=final_thinking,
    )

    collected = asyncio.run(helper.collect_event_data(handler))

    assert collected.thinking == (
        "Ich suche in den FAQ.\n\nIch suche in den FAQ.\n\nIch formuliere die Antwort."
    )
    assert collected.tool_calls == [
        {
            "tool_name": "faq_lookup",
            "tool_input": "Wie registriere ich mich?",
            "tool_output": "Keine FAQ-Treffer",
            "is_error": False,
        }
    ]
    assert collected.has_tool_error is False
    assert collected.has_no_match is True


@pytest.mark.unit
def test_record_tool_observation_keeps_structured_child_output(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)
    root = FakeObservation()
    tool_payload = {
        "matches": [
            {
                "faq_id": "faq_1",
                "answer": "Klicke auf Registrieren.",
                "score": 0.9,
            }
        ]
    }
    event = ToolCallResult(
        tool_name="faq_lookup",
        tool_kwargs={"question": "Wie registriere ich mich?"},
        tool_id="tool-match",
        tool_output=ToolOutput(
            tool_name="faq_lookup",
            content=json.dumps(tool_payload, ensure_ascii=False),
            raw_input={},
            raw_output=tool_payload,
            is_error=False,
        ),
        return_direct=False,
    )
    final_event = AgentOutput(
        response=ChatMessage(role="assistant", content="Klicke auf Registrieren."),
        current_agent_name="FAQAgent",
        raw={"message": {"thinking": "Ich habe einen passenden FAQ-Treffer."}},
    )
    handler = FakeHandler(events=[final_event, event], result=final_event)

    collected = asyncio.run(helper.collect_event_data(handler, root))

    assert collected.tool_calls == [
        {
            "tool_name": "faq_lookup",
            "tool_input": "Wie registriere ich mich?",
            "tool_output": "faq_1: Klicke auf Registrieren.",
            "is_error": False,
        }
    ]
    assert root.children[0].updates == [{"output": tool_payload}]
    assert root.children[0].ended is True


@pytest.mark.unit
def test_update_root_observation_marks_no_match(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)
    root = FakeObservation()

    helper.update_root_observation(
        root=root,
        answer="Fallback",
        collected=CollectedEventData(
            thinking="Ich konnte keinen Treffer finden.",
            tool_calls=[
                {
                    "tool_name": "faq_lookup",
                    "tool_input": "Unbekannte Frage",
                    "tool_output": "Keine FAQ-Treffer",
                    "is_error": False,
                }
            ],
            has_no_match=True,
        ),
    )

    assert root.updates[-1] == {
        "output": {"answer": "Fallback"},
        "metadata": {
            "system_prompt_version": LANGFUSE_SYSTEM_PROMPT_VERSION,
            "tool_count": 1,
            "tool_error": False,
            "no_match": True,
        },
        "level": "WARNING",
        "status_message": "No FAQ match found.",
    }


@pytest.mark.unit
def test_update_root_observation_marks_tool_errors(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)
    root = FakeObservation()

    helper.update_root_observation(
        root=root,
        answer="Fallback",
        collected=CollectedEventData(
            thinking="Ich habe ein Tool-Problem gesehen.",
            tool_calls=[
                {
                    "tool_name": "faq_lookup",
                    "tool_input": "Frage",
                    "tool_output": "timeout",
                    "is_error": True,
                }
            ],
            has_tool_error=True,
        ),
    )

    assert root.updates[-1] == {
        "output": {"answer": "Fallback"},
        "metadata": {
            "system_prompt_version": LANGFUSE_SYSTEM_PROMPT_VERSION,
            "tool_count": 1,
            "tool_error": True,
            "no_match": False,
        },
        "level": "ERROR",
        "status_message": "Tool or agent execution failed; technical fallback returned.",
    }


@pytest.mark.unit
def test_summarize_tool_input_keeps_structured_multi_field_values(settings_factory) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)

    assert helper.summarize_tool_input(
        {"question": "Wie registriere ich mich?", "locale": "de"}
    ) == {"question": "Wie registriere ich mich?", "locale": "de"}


@pytest.mark.unit
def test_start_trace_observation_and_propagation_when_configured(
    monkeypatch, settings_factory
) -> None:
    settings = settings_factory()
    helper = AgentTraceHelper(settings)
    observation = FakeObservation()
    langfuse_client = FakeLangfuseClient(observation=observation)
    session_calls: list[dict[str, Any]] = []

    def fake_propagate_attributes(**kwargs: Any) -> FakeSessionContext:
        session_calls.append(kwargs)
        return FakeSessionContext()

    monkeypatch.setattr("customer_bot.agent.tracing.get_client", lambda: langfuse_client)
    monkeypatch.setattr(
        "customer_bot.agent.tracing.propagate_attributes",
        fake_propagate_attributes,
    )

    with helper.propagate_trace_attributes("session-42"):
        with helper.start_trace_observation("Unbekannte Frage", "session-42") as root:
            assert root is observation

    assert langfuse_client.calls == [
        {
            "name": LANGFUSE_TRACE_NAME,
            "as_type": "agent",
            "input": {"user_message": "Unbekannte Frage"},
            "metadata": {
                "session_id": "session-42",
                "system_prompt_version": LANGFUSE_SYSTEM_PROMPT_VERSION,
            },
        }
    ]
    assert session_calls == [
        {
            "session_id": "session-42",
            "trace_name": LANGFUSE_TRACE_NAME,
            "tags": ["chat", "faq-agent"],
        }
    ]


@pytest.mark.unit
def test_start_trace_observation_and_propagation_when_disabled(
    monkeypatch, settings_factory
) -> None:
    settings = settings_factory(LANGFUSE_PUBLIC_KEY="", LANGFUSE_SECRET_KEY="")
    helper = AgentTraceHelper(settings)
    session_calls: list[dict[str, Any]] = []

    def fake_propagate_attributes(**kwargs: Any):
        session_calls.append(kwargs)
        raise AssertionError("propagate_attributes should not be called when disabled")

    monkeypatch.setattr(
        "customer_bot.agent.tracing.propagate_attributes",
        fake_propagate_attributes,
    )

    with helper.propagate_trace_attributes("session-no-langfuse"):
        with helper.start_trace_observation("Hallo", "session-no-langfuse") as root:
            assert root is None

    assert session_calls == []
