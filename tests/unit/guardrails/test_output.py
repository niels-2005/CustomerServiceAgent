from __future__ import annotations

import asyncio

import pytest

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.guardrails.models import GuardrailCheck
from customer_bot.guardrails.output import OutputGuardPipeline
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from tests.unit.agent.fakes import FakeObservation


class FakeOutputPiiGuard:
    def __init__(self, *, blocked: bool = False, sanitized_text: str = "answer") -> None:
        self.blocked = blocked
        self.sanitized_text = sanitized_text

    async def check(self, answer: str):
        return (
            self.blocked,
            self.sanitized_text,
            GuardrailCheck(
                name="output_sensitive_data",
                decision="rewrite" if self.blocked else "allow",
                triggered=self.blocked,
                decision_source="pii_detector",
                llm_called=False,
            ),
        )


class FakeSemanticGuard:
    def __init__(self, check: GuardrailCheck | Exception) -> None:
        self.check_result = check
        self.calls = 0

    async def check(self, *args, **kwargs):
        del args, kwargs
        self.calls += 1
        if isinstance(self.check_result, Exception):
            raise self.check_result
        return self.check_result


def _pipeline(settings, *, pii_guard, grounding_guard, bias_guard):
    return OutputGuardPipeline(
        settings=settings,
        trace_helper=GuardrailTraceHelper(settings),
        output_pii_guard=pii_guard,
        grounding_guard=grounding_guard,
        bias_guard=bias_guard,
    )


@pytest.mark.unit
def test_output_pipeline_rewrites_immediately_on_output_pii(settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=True)
    grounding_guard = FakeSemanticGuard(GuardrailCheck(name="grounding", decision="allow"))
    bias_guard = FakeSemanticGuard(GuardrailCheck(name="bias", decision="allow"))
    pipeline = _pipeline(
        settings,
        pii_guard=FakeOutputPiiGuard(blocked=True, sanitized_text="[redacted]"),
        grounding_guard=grounding_guard,
        bias_guard=bias_guard,
    )

    result = asyncio.run(
        pipeline.run(
            user_message="Hallo",
            answer="secret answer",
            compact_history="",
            agent_result=AgentAnswerResult(answer="secret answer"),
            parent_observation=FakeObservation(),
        )
    )

    assert result.action == "rewrite"
    assert result.reason == "output_sensitive_data"
    assert result.sanitized is True
    assert grounding_guard.calls == 0
    assert bias_guard.calls == 0


@pytest.mark.unit
def test_output_pipeline_fails_open_when_configured(settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=True, guardrails_fail_closed=False)
    pipeline = _pipeline(
        settings,
        pii_guard=FakeOutputPiiGuard(blocked=False, sanitized_text="answer"),
        grounding_guard=FakeSemanticGuard(RuntimeError("grounding failed")),
        bias_guard=FakeSemanticGuard(GuardrailCheck(name="bias", decision="allow")),
    )

    result = asyncio.run(
        pipeline.run(
            user_message="Hallo",
            answer="answer",
            compact_history="",
            agent_result=AgentAnswerResult(answer="answer"),
        )
    )

    assert result.action == "allow"


@pytest.mark.unit
def test_output_pipeline_falls_back_when_fail_closed(settings_factory) -> None:
    settings = settings_factory(guardrails_enabled=True, guardrails_fail_closed=True)
    pipeline = _pipeline(
        settings,
        pii_guard=FakeOutputPiiGuard(blocked=False, sanitized_text="answer"),
        grounding_guard=FakeSemanticGuard(RuntimeError("grounding failed")),
        bias_guard=FakeSemanticGuard(GuardrailCheck(name="bias", decision="allow")),
    )

    result = asyncio.run(
        pipeline.run(
            user_message="Hallo",
            answer="answer",
            compact_history="",
            agent_result=AgentAnswerResult(answer="answer"),
        )
    )

    assert result.action == "fallback"
    assert result.reason == "guardrail_error"
