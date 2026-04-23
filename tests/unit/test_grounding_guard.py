from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.guardrails.validators.grounding import GroundingGuard


class _GroundingDecisionResult(BaseModel):
    decision: str
    reason: str
    rewrite_hint: str | None = None


class _FakeExecutor:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def run(self, **kwargs):
        del kwargs

        class _Result:
            def __init__(self, payload: dict[str, object]) -> None:
                self.validated_output = _GroundingDecisionResult.model_validate(payload)

        return _Result(self._payload)


@pytest.mark.unit
def test_grounding_guard_corrects_contradictory_positive_reason(settings_factory) -> None:
    guard = GroundingGuard(
        settings_factory(),
        _FakeExecutor(
            {
                "decision": "fallback",
                "reason": "The answer directly matches the evidence.",
                "rewrite_hint": None,
            }
        ),
    )

    result = asyncio.run(
        guard.check(
            user_message="Wie kann ich einen Account erstellen?",
            answer="Du kannst ein Konto erstellen, indem du auf Registrieren klickst.",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Du kannst ein Konto erstellen, indem du auf Registrieren klickst.",
                evidence=[
                    "faq_3: Du kannst ein Konto erstellen, indem du auf Registrieren klickst."
                ],
            ),
        )
    )

    assert result.decision == "allow"
    assert result.triggered is False


@pytest.mark.unit
def test_grounding_guard_keeps_real_fallback(settings_factory) -> None:
    guard = GroundingGuard(
        settings_factory(),
        _FakeExecutor(
            {
                "decision": "fallback",
                "reason": "The evidence does not support the answer.",
                "rewrite_hint": None,
            }
        ),
    )

    result = asyncio.run(
        guard.check(
            user_message="Wie kann ich einen Account erstellen?",
            answer="Du musst den Support anrufen.",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Du musst den Support anrufen.",
                evidence=[
                    "faq_3: Du kannst ein Konto erstellen, indem du auf Registrieren klickst."
                ],
            ),
        )
    )

    assert result.decision == "fallback"
    assert result.triggered is True
