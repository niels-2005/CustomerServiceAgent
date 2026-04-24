from __future__ import annotations

import asyncio

import pytest

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.guardrails.input import InputGuardPipeline
from customer_bot.guardrails.models import GuardrailCheck
from customer_bot.guardrails.output import OutputGuardPipeline
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from tests.unit.agent_fakes import FakeObservation


class _FakePiiGuard:
    def __init__(self, name: str) -> None:
        self._name = name

    async def check(self, text: str):
        return (
            False,
            text,
            GuardrailCheck(name=self._name, decision="allow", reason="ok", triggered=False),
        )


class _FakeInputGuard:
    def __init__(self, name: str) -> None:
        self._name = name

    async def check(self, user_message: str, compact_history: str, parent_observation=None):
        del user_message, compact_history, parent_observation
        return GuardrailCheck(
            name=self._name,
            decision="allow",
            reason="ok",
            triggered=False,
        )


class _FakeOutputGuard:
    def __init__(self, name: str) -> None:
        self._name = name

    async def check(self, *args, **kwargs):
        del args, kwargs
        return GuardrailCheck(
            name=self._name,
            decision="allow",
            reason="ok",
            triggered=False,
        )


@pytest.mark.unit
def test_input_pipeline_creates_guardrail_child_observations(settings_factory) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    pipeline = InputGuardPipeline(
        settings=settings,
        trace_helper=GuardrailTraceHelper(settings),
        pii_guard=_FakePiiGuard("secret_pii"),
        prompt_injection_guard=_FakeInputGuard("prompt_injection"),
        topic_relevance_guard=_FakeInputGuard("topic_relevance"),
        escalation_guard=_FakeInputGuard("escalation"),
    )
    root = FakeObservation()

    result = asyncio.run(
        pipeline.run(
            user_message="Wie kann ich einen Account erstellen?",
            chat_history=[],
            parent_observation=root,
        )
    )

    assert result.action == "allow"
    assert [child.start_kwargs["name"] for child in root.children] == [
        "secret_pii",
        "prompt_injection",
        "topic_relevance",
        "escalation",
    ]
    assert root.children[0].start_kwargs["as_type"] == "guardrail"
    assert root.children[1].updates[-1]["metadata"]["decision"] == "allow"
    assert root.children[1].updates[-1]["metadata"]["decision_source"] == "llm"
    assert root.children[1].updates[-1]["metadata"]["llm_called"] is True


@pytest.mark.unit
def test_output_pipeline_creates_guardrail_child_observations(settings_factory) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    pipeline = OutputGuardPipeline(
        settings=settings,
        trace_helper=GuardrailTraceHelper(settings),
        output_pii_guard=_FakePiiGuard("output_sensitive_data"),
        grounding_guard=_FakeOutputGuard("grounding"),
        bias_guard=_FakeOutputGuard("bias"),
    )
    root = FakeObservation()

    result = asyncio.run(
        pipeline.run(
            user_message="Wie kann ich einen Account erstellen?",
            answer="Klicke auf Registrieren.",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Klicke auf Registrieren.",
                evidence=["faq_1: Klicke auf Registrieren."],
            ),
            parent_observation=root,
        )
    )

    assert result.action == "allow"
    assert [child.start_kwargs["name"] for child in root.children] == [
        "output_sensitive_data",
        "grounding",
        "bias",
    ]
    assert root.children[1].start_kwargs["as_type"] == "guardrail"
    assert root.children[2].updates[-1]["metadata"]["decision"] == "allow"
    assert root.children[2].updates[-1]["metadata"]["decision_source"] == "llm"
    assert root.children[2].updates[-1]["metadata"]["llm_called"] is True
