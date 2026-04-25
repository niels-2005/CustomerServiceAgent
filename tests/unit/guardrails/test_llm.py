from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel, ValidationError

from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.tracing import GuardrailTraceHelper


class _DecisionModel(BaseModel):
    decision: str
    reason: str


class _FakeClient:
    def __init__(self, payload: str) -> None:
        self.model = "gpt-test"
        self._payload = payload

    async def complete_structured(self, **kwargs) -> BaseModel:
        output_model = kwargs["output_model"]
        return output_model.model_validate_json(self._payload)


@pytest.mark.unit
def test_llm_guard_executor_validates_json_with_pydantic(settings_factory) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    executor = LlmGuardExecutor(
        client=_FakeClient('{"decision":"allow","reason":"ok","score":0.91}'),
        trace_helper=GuardrailTraceHelper(settings),
    )

    result = asyncio.run(
        executor.run(
            name="grounding",
            system_prompt="system",
            user_prompt="user",
            output_model=_DecisionModel,
        )
    )

    assert result.validated_output == _DecisionModel(decision="allow", reason="ok")


@pytest.mark.unit
def test_llm_guard_executor_raises_for_schema_mismatch(settings_factory) -> None:
    settings = settings_factory(
        guardrails_enabled=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )
    executor = LlmGuardExecutor(
        client=_FakeClient('{"decision":"allow"}'),
        trace_helper=GuardrailTraceHelper(settings),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            executor.run(
                name="grounding",
                system_prompt="system",
                user_prompt="user",
                output_model=_DecisionModel,
            )
        )
