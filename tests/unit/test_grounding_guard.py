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
def test_grounding_guard_allows_meta_answer_without_tool_call(settings_factory) -> None:
    executor = _FakeExecutor(
        {
            "decision": "allow",
            "reason": "This is a brief greeting and offer to help without unsupported facts.",
            "rewrite_hint": None,
        }
    )
    guard = GroundingGuard(settings_factory(), executor)

    result = asyncio.run(
        guard.check(
            user_message="Hallo",
            answer="Hallo! Wie kann ich Ihnen heute helfen?",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Hallo! Wie kann ich Ihnen heute helfen?",
                tool_calls=[],
                evidence=[],
                used_history_only=False,
            ),
        )
    )

    assert result.decision == "allow"
    assert result.triggered is False
    assert executor.calls
    assert "No-tool answer: true" in str(executor.calls[0]["user_prompt"])
    assert "Tool call count: 0" in str(executor.calls[0]["user_prompt"])


@pytest.mark.unit
def test_grounding_guard_fallbacks_on_hallucinated_answer_without_tool_call(
    settings_factory,
) -> None:
    guard = GroundingGuard(
        settings_factory(),
        _FakeExecutor(
            {
                "decision": "fallback",
                "reason": "The answer makes unsupported product claims without evidence.",
                "rewrite_hint": None,
            }
        ),
    )

    result = asyncio.run(
        guard.check(
            user_message="Was ist Produkt XYZ?",
            answer="Produkt XYZ ist unser Premium-Abo mit 24/7 Support.",
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="Produkt XYZ ist unser Premium-Abo mit 24/7 Support.",
                tool_calls=[],
                evidence=[],
                used_history_only=False,
            ),
        )
    )

    assert result.decision == "fallback"
    assert result.triggered is True


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


@pytest.mark.unit
def test_grounding_guard_receives_full_product_evidence(settings_factory) -> None:
    executor = _FakeExecutor(
        {
            "decision": "allow",
            "reason": "The answer is directly supported by the product evidence.",
            "rewrite_hint": None,
        }
    )
    guard = GroundingGuard(settings_factory(), executor)

    result = asyncio.run(
        guard.check(
            user_message="Und was beinhaltet das Produkt VoiceHub Conference Mic",
            answer=(
                "Hier sind die wichtigsten Eckdaten zum VoiceHub Conference Mic:\n\n"
                "- Produkt: VoiceHub Conference Mic\n"
                "- Kategorie: Audio\n"
                "- Preis: 89,90 EUR\n"
                "- Verfügbarkeit: verfügbar\n"
                "- Beschreibung: Desktop-Mikrofon fuer Meetings, Podcasts und Sprachaufnahmen\n"
                "- Wichtige Merkmale: USB-C, Noise Reduction, Mute-Taste, Stativgewinde\n"
                "- Produktseite: https://nexamarket.example/products/voicehub-conference-mic"
            ),
            compact_history="",
            agent_result=AgentAnswerResult(
                answer="",
                tool_calls=[{"tool_name": "product_lookup"}],
                evidence=[
                    "prod_027: VoiceHub Conference Mic | "
                    "description=Desktop-Mikrofon fuer Meetings, Podcasts und Sprachaufnahmen. | "
                    "category=audio | price=89.90 EUR | availability=available | "
                    "features=USB-C|Noise Reduction|Mute-Taste|Stativgewinde | "
                    "url=https://nexamarket.example/products/voicehub-conference-mic"
                ],
            ),
        )
    )

    assert result.decision == "allow"
    assert result.triggered is False
    assert executor.calls
    prompt = str(executor.calls[0]["user_prompt"])
    assert "price=89.90 EUR" in prompt
    assert "availability=available" in prompt
    assert "features=USB-C|Noise Reduction|Mute-Taste|Stativgewinde" in prompt
    assert "url=https://nexamarket.example/products/voicehub-conference-mic" in prompt
