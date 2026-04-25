from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _BiasDecision(BaseModel):
    decision: Literal["allow", "rewrite", "fallback"]
    reason: str
    rewrite_hint: str | None = None


class BiasGuard:
    def __init__(self, settings: Settings, executor: LlmGuardExecutor) -> None:
        self._settings = settings
        self._executor = executor

    async def check(self, answer: str, parent_observation=None) -> GuardrailCheck:
        prompt = self._settings.guardrails.output.bias.user_prompt_template.format(
            answer=answer,
            bias_terms=", ".join(self._settings.guardrails.output.bias.bias_terms),
        )
        result = await self._executor.run(
            name="bias",
            system_prompt=self._settings.guardrails.output.bias.system_prompt,
            user_prompt=prompt,
            output_model=_BiasDecision,
            parent_observation=parent_observation,
        )
        validated = _BiasDecision.model_validate(result.validated_output.model_dump())
        return GuardrailCheck(
            name="bias",
            decision=validated.decision,
            reason=validated.reason,
            rewrite_hint=validated.rewrite_hint,
            triggered=validated.decision != "allow",
            decision_source="llm",
            llm_called=True,
        )
