from __future__ import annotations

import asyncio

import pytest

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.guardrails.models import (
    GuardrailInputResult,
    GuardrailOutputResult,
    GuardrailRewriteResult,
)
from customer_bot.guardrails.service import GuardrailService


class FakePipeline:
    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def run(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeRewriter:
    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def rewrite(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


@pytest.mark.unit
def test_guardrail_service_compacts_recent_history(settings_factory) -> None:
    from llama_index.core.base.llms.types import ChatMessage

    settings = settings_factory()
    service = GuardrailService(settings=settings, llm_client=None)

    compact = service._compact_history(
        [
            ChatMessage(role="user", content="one"),
            ChatMessage(role="assistant", content="two"),
            ChatMessage(role="user", content="three"),
            ChatMessage(role="assistant", content="four"),
            ChatMessage(role="user", content="five"),
        ]
    )

    assert compact == (
        "MessageRole.ASSISTANT: two\n"
        "MessageRole.USER: three\n"
        "MessageRole.ASSISTANT: four\n"
        "MessageRole.USER: five"
    )


@pytest.mark.unit
def test_guardrail_service_evaluate_input_traces_stage_result(settings_factory) -> None:
    settings = settings_factory()
    service = GuardrailService(settings=settings, llm_client=None)
    service._input_pipeline = FakePipeline(
        GuardrailInputResult(
            action="blocked",
            reason="secret_pii",
            message="blocked",
            sanitized_user_message="[redacted]",
            sanitized=True,
        )
    )

    result = asyncio.run(service.evaluate_input(user_message="secret", chat_history=[]))

    assert result.action == "blocked"
    assert service._input_pipeline.calls[0]["user_message"] == "secret"


@pytest.mark.unit
def test_guardrail_service_evaluate_output_passes_compact_history(settings_factory) -> None:
    from llama_index.core.base.llms.types import ChatMessage

    settings = settings_factory()
    service = GuardrailService(settings=settings, llm_client=None)
    service._output_pipeline = FakePipeline(
        GuardrailOutputResult(
            action="allow",
            reason=None,
            rewrite_hint=None,
        )
    )

    result = asyncio.run(
        service.evaluate_output(
            user_message="Hallo",
            answer="Antwort",
            chat_history=[
                ChatMessage(role="user", content="one"),
                ChatMessage(role="assistant", content="two"),
            ],
            agent_result=AgentAnswerResult(answer="Antwort"),
        )
    )

    assert result.action == "allow"
    assert service._output_pipeline.calls[0]["compact_history"] == (
        "MessageRole.USER: one\nMessageRole.ASSISTANT: two"
    )


@pytest.mark.unit
def test_guardrail_service_rewrite_output_passes_evidence(settings_factory) -> None:
    settings = settings_factory()
    service = GuardrailService(settings=settings, llm_client=None)
    service._rewrite_service = FakeRewriter(GuardrailRewriteResult(answer="safe answer"))

    result = asyncio.run(
        service.rewrite_output(
            answer="unsafe",
            rewrite_hint="hint",
            user_message="Hallo",
            agent_result=AgentAnswerResult(answer="unsafe", evidence=["fact-1"]),
        )
    )

    assert result.answer == "safe answer"
    assert service._rewrite_service.calls[0]["evidence"] == ["fact-1"]
