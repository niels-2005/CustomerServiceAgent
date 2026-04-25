from __future__ import annotations

import asyncio

import pytest

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.chat.service import ChatService
from customer_bot.guardrails.presidio import PresidioDetectionResult
from customer_bot.guardrails.service import GuardrailService
from customer_bot.memory.backend import InMemorySessionMemoryBackend


class RecordingAgentService:
    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.calls: list[tuple[str, str]] = []

    async def answer(
        self,
        user_message: str,
        chat_history,
        session_id: str,
        parent_observation=None,
    ) -> AgentAnswerResult:
        del chat_history, parent_observation
        self.calls.append((user_message, session_id))
        return AgentAnswerResult(answer=self._answer)


class StubGuardrailClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)
        self.model = "guardrail-stub"

    async def complete_structured(self, *, system_prompt: str, user_prompt: str, output_model):
        del system_prompt, user_prompt
        payload = self._responses.pop(0)
        return output_model.model_validate(payload)


@pytest.mark.integration
def test_chat_service_with_real_guardrails_blocks_and_persists_sanitized_turn(
    settings_factory,
) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        guardrails_input_pii_enabled=True,
        guardrails_input_pii_custom_patterns=[r"TESTSECRET\d+"],
        guardrails_prompt_injection_enabled=False,
        guardrails_topic_relevance_enabled=False,
        guardrails_escalation_enabled=False,
        guardrails_output_pii_enabled=False,
        guardrails_grounding_enabled=False,
        guardrails_bias_enabled=False,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    memory = InMemorySessionMemoryBackend(max_turns=settings.memory.max_turns)
    agent = RecordingAgentService(answer="unused")
    service = ChatService(
        memory_backend=memory,
        agent_service=agent,
        settings=settings,
        guardrail_service=GuardrailService(settings=settings, llm_client=None),
    )

    result = asyncio.run(service.chat("Meine ID ist TESTSECRET42", session_id="s-block"))
    history = asyncio.run(memory.get_history("s-block"))

    assert result.status == "blocked"
    assert result.guardrail_reason == "secret_pii"
    assert result.sanitized is True
    assert result.answer == settings.guardrails.input.pii.message
    assert agent.calls == []
    assert history[0].content == "Meine ID ist [redacted]"
    assert history[1].content == settings.guardrails.input.pii.message


@pytest.mark.integration
def test_chat_service_with_real_guardrails_handoffs_request(settings_factory) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        guardrails_input_pii_enabled=False,
        guardrails_prompt_injection_enabled=False,
        guardrails_topic_relevance_enabled=False,
        guardrails_escalation_enabled=True,
        guardrails_output_pii_enabled=False,
        guardrails_grounding_enabled=False,
        guardrails_bias_enabled=False,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    memory = InMemorySessionMemoryBackend(max_turns=settings.memory.max_turns)
    agent = RecordingAgentService(answer="unused")
    service = ChatService(
        memory_backend=memory,
        agent_service=agent,
        settings=settings,
        guardrail_service=GuardrailService(
            settings=settings,
            llm_client=StubGuardrailClient(
                [{"decision": "handoff", "reason": "Legal escalation requires support."}]
            ),
        ),
    )

    result = asyncio.run(service.chat("Ich reiche Klage ein", session_id="s-handoff"))
    history = asyncio.run(memory.get_history("s-handoff"))

    assert result.status == "handoff"
    assert result.guardrail_reason == "escalation"
    assert result.handoff_required is True
    assert agent.calls == []
    assert history[0].content == "Ich reiche Klage ein"
    assert history[1].content == settings.guardrails.input.escalation.message


@pytest.mark.integration
def test_chat_service_rewrites_and_rechecks_output_with_real_guardrail_service(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    monkeypatch.setattr(
        "customer_bot.guardrails.validators.secret_pii._BasePiiGuard._detect_with_presidio",
        lambda self, text: PresidioDetectionResult(
            sanitized_text=text,
            triggered=False,
            reason="No sensitive data detected.",
        ),
    )
    settings = settings_factory(
        guardrails_enabled=True,
        guardrails_input_pii_enabled=False,
        guardrails_prompt_injection_enabled=False,
        guardrails_topic_relevance_enabled=False,
        guardrails_escalation_enabled=False,
        guardrails_output_pii_enabled=True,
        guardrails_output_pii_custom_patterns=[r"SECRET\d+"],
        guardrails_grounding_enabled=False,
        guardrails_bias_enabled=False,
        guardrails_rewrite_enabled=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    memory = InMemorySessionMemoryBackend(max_turns=settings.memory.max_turns)
    agent = RecordingAgentService(answer="Teile SECRET123 nicht.")
    guardrail_service = GuardrailService(
        settings=settings,
        llm_client=StubGuardrailClient([{"answer": "Sichere Antwort", "reason": "secret removed"}]),
    )
    service = ChatService(
        memory_backend=memory,
        agent_service=agent,
        settings=settings,
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Bitte antworte", session_id="s-rewrite"))
    history = asyncio.run(memory.get_history("s-rewrite"))

    assert result.status == "answered"
    assert result.retry_used is True
    assert result.sanitized is True
    assert result.answer == "Sichere Antwort"
    assert history[-1].content == "Sichere Antwort"


@pytest.mark.integration
def test_chat_service_falls_back_when_rewritten_answer_still_fails_output_checks(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    monkeypatch.setattr(
        "customer_bot.guardrails.validators.secret_pii._BasePiiGuard._detect_with_presidio",
        lambda self, text: PresidioDetectionResult(
            sanitized_text=text,
            triggered=False,
            reason="No sensitive data detected.",
        ),
    )
    settings = settings_factory(
        guardrails_enabled=True,
        guardrails_input_pii_enabled=False,
        guardrails_prompt_injection_enabled=False,
        guardrails_topic_relevance_enabled=False,
        guardrails_escalation_enabled=False,
        guardrails_output_pii_enabled=True,
        guardrails_output_pii_custom_patterns=[r"SECRET\d+"],
        guardrails_grounding_enabled=False,
        guardrails_bias_enabled=False,
        guardrails_rewrite_enabled=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    memory = InMemorySessionMemoryBackend(max_turns=settings.memory.max_turns)
    agent = RecordingAgentService(answer="Teile SECRET123 nicht.")
    guardrail_service = GuardrailService(
        settings=settings,
        llm_client=StubGuardrailClient(
            [{"answer": "SECRET123 bleibt sichtbar", "reason": "unchanged"}]
        ),
    )
    service = ChatService(
        memory_backend=memory,
        agent_service=agent,
        settings=settings,
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Bitte antworte", session_id="s-fallback"))

    assert result.status == "fallback"
    assert result.guardrail_reason == "output_sensitive_data"
    assert result.retry_used is True
    assert result.answer == settings.messages.error_fallback_text
