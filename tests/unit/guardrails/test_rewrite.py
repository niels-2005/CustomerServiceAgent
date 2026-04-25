from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from customer_bot.guardrails.rewrite import RewriteService
from customer_bot.guardrails.tracing import GuardrailTraceHelper


class FakeRewriteExecutor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def run(self, **kwargs):
        self.calls.append(kwargs)

        class _Output(BaseModel):
            answer: str
            reason: str | None = None

        class _Result:
            validated_output = _Output(answer="Safer answer", reason="rewritten")

        return _Result()


@pytest.mark.unit
def test_rewrite_service_returns_original_answer_when_disabled(settings_factory) -> None:
    settings = settings_factory(guardrails_rewrite_enabled=False)
    executor = FakeRewriteExecutor()
    service = RewriteService(settings, executor, GuardrailTraceHelper(settings))

    result = asyncio.run(
        service.rewrite(
            answer="original",
            rewrite_hint="Remove secrets",
            evidence=["fact-1"],
            user_message="Hallo",
        )
    )

    assert result.answer == "original"
    assert executor.calls == []


@pytest.mark.unit
def test_rewrite_service_formats_prompt_and_returns_validated_answer(settings_factory) -> None:
    settings = settings_factory(guardrails_rewrite_enabled=True)
    executor = FakeRewriteExecutor()
    service = RewriteService(settings, executor, GuardrailTraceHelper(settings))

    result = asyncio.run(
        service.rewrite(
            answer="original",
            rewrite_hint="Remove secrets",
            evidence=["fact-1", "fact-2"],
            user_message="Hallo",
        )
    )

    assert result.answer == "Safer answer"
    assert executor.calls[0]["name"] == "rewrite"
    assert "original" in executor.calls[0]["user_prompt"]
    assert "Remove secrets" in executor.calls[0]["user_prompt"]
    assert "fact-1\nfact-2" in executor.calls[0]["user_prompt"]
