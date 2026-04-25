from __future__ import annotations

import asyncio
import logging

import pytest

from customer_bot.guardrails.input import InputGuardPipeline
from customer_bot.guardrails.models import GuardrailCheck
from customer_bot.guardrails.sanitization import sanitize_for_tracing
from customer_bot.guardrails.tracing import GuardrailTraceHelper


@pytest.mark.unit
def test_sanitizer_keeps_operational_metadata_visible(settings_factory) -> None:
    settings = settings_factory()

    sanitized = sanitize_for_tracing(
        {
            "session_id": "session-1",
            "request_id": "req-1",
            "status": "blocked",
            "user_message": "secret sk-1234567890abcdef",
        },
        settings,
    )

    assert sanitized["session_id"] == "session-1"
    assert sanitized["request_id"] == "req-1"
    assert sanitized["status"] == "blocked"
    assert sanitized["user_message"] == "secret [redacted]"


@pytest.mark.unit
def test_sanitizer_keeps_normal_user_message_visible(settings_factory) -> None:
    settings = settings_factory()

    sanitized = sanitize_for_tracing(
        {
            "user_message": "Wie kann ich einen Account erstellen?",
            "answer": "Klicke auf Registrieren.",
        },
        settings,
    )

    assert sanitized["user_message"] == "Wie kann ich einen Account erstellen?"
    assert sanitized["answer"] == "Klicke auf Registrieren."


@pytest.mark.unit
def test_langfuse_mask_accepts_data_keyword(settings_factory) -> None:
    settings = settings_factory()

    from customer_bot.guardrails.sanitization import build_langfuse_mask

    mask = build_langfuse_mask(settings)
    sanitized = mask(data={"user_message": "secret sk-1234567890abcdef"})

    assert sanitized["user_message"] == "secret [redacted]"


class _FakePiiGuard:
    async def check(self, text: str):
        del text
        return (
            False,
            "Hallo",
            GuardrailCheck(name="secret_pii", decision="allow", triggered=False),
        )


class _RaisingGuard:
    def __init__(self, name: str) -> None:
        self._name = name

    async def check(self, user_message: str, compact_history: str, parent_observation=None):
        del user_message, compact_history, parent_observation
        raise RuntimeError(f"{self._name} boom")


@pytest.mark.unit
def test_input_guard_pipeline_logs_and_fails_closed(caplog, settings_factory) -> None:
    pipeline = InputGuardPipeline(
        settings=settings_factory(
            guardrails_enabled=True,
            LANGFUSE_PUBLIC_KEY="",
            LANGFUSE_SECRET_KEY="",
        ),
        trace_helper=GuardrailTraceHelper(
            settings_factory(
                guardrails_enabled=True,
                LANGFUSE_PUBLIC_KEY="",
                LANGFUSE_SECRET_KEY="",
            )
        ),
        pii_guard=_FakePiiGuard(),
        prompt_injection_guard=_RaisingGuard("prompt_injection"),
        topic_relevance_guard=_RaisingGuard("topic_relevance"),
        escalation_guard=_RaisingGuard("escalation"),
    )

    with caplog.at_level(logging.ERROR):
        result = asyncio.run(pipeline.run(user_message="Hallo", chat_history=[]))

    assert result.action == "blocked"
    assert result.reason == "guardrail_error"
    assert "Input guard pipeline failed" in caplog.text
