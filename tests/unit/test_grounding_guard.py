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
        self.calls: list[dict[str, object]] = []

    async def run(self, **kwargs):
        self.calls.append(kwargs)

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
def test_grounding_guard_allows_grounded_no_match_answer(settings_factory) -> None:
    executor = _FakeExecutor(
        {
            "decision": "allow",
            "reason": "The answer is supported by the explicit no-match evidence.",
            "rewrite_hint": None,
        }
    )
    guard = GroundingGuard(settings_factory(), executor)

    result = asyncio.run(
        guard.check(
            user_message="Erzähl mir mehr über das Produkt Maweees",
            answer="Ich konnte dazu in den FAQs keine verlässlichen Informationen finden.",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Ich konnte dazu in den FAQs keine verlässlichen Informationen finden.",
                evidence=["faq_lookup: Kein verlässlicher FAQ-Treffer für diese Anfrage gefunden."],
            ),
        )
    )

    assert result.decision == "allow"
    assert result.triggered is False
    assert executor.calls
    assert "Kein verlässlicher FAQ-Treffer" in str(executor.calls[0]["user_prompt"])


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


@pytest.mark.unit
def test_grounding_guard_fallbacks_on_hallucinated_no_match_answer(settings_factory) -> None:
    guard = GroundingGuard(
        settings_factory(),
        _FakeExecutor(
            {
                "decision": "fallback",
                "reason": "The explicit no-match evidence does not support product details.",
                "rewrite_hint": None,
            }
        ),
    )

    result = asyncio.run(
        guard.check(
            user_message="Erzähl mir mehr über das Produkt Maweees",
            answer="Maweees kostet 49 Euro und ist aktuell lieferbar.",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Maweees kostet 49 Euro und ist aktuell lieferbar.",
                evidence=["faq_lookup: Kein verlässlicher FAQ-Treffer für diese Anfrage gefunden."],
            ),
        )
    )

    assert result.decision == "fallback"
    assert result.triggered is True
