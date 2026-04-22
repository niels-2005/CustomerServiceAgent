from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _BiasDecision(BaseModel):
    decision: str
    score: float
    reason: str
    rewrite_hint: str | None = None


class BiasGuard:
    def __init__(self, settings: Settings, executor: LlmGuardExecutor) -> None:
        self._settings = settings
        self._executor = executor

    async def check(self, answer: str, parent_observation=None) -> GuardrailCheck:
        lowered = answer.lower()
        if any(term.lower() in lowered for term in self._settings.guardrails_bias_heuristic_terms):
            return GuardrailCheck(
                name="bias",
                decision="rewrite",
                score=1.0,
                reason="Bias heuristic matched.",
                rewrite_hint="Entferne pauschalisierende oder diskriminierende Formulierungen.",
                triggered=True,
            )

        prompt = self._settings.guardrails_bias_user_prompt_template.format(
            answer=answer,
            bias_terms=", ".join(self._settings.guardrails_bias_heuristic_terms),
        )
        result = await self._executor.run(
            name="bias",
            system_prompt=self._settings.guardrails_bias_system_prompt,
            user_prompt=prompt,
            output_model=_BiasDecision,
            parent_observation=parent_observation,
        )
        validated = _BiasDecision.model_validate(result.validated_output.model_dump())
        decision = validated.decision
        if validated.score < self._settings.guardrails_bias_threshold:
            decision = "allow"
        typed_decision = cast(Literal["allow", "rewrite", "fallback"], decision)
        return GuardrailCheck(
            name="bias",
            decision=typed_decision if decision in {"allow", "rewrite", "fallback"} else "fallback",
            score=validated.score,
            reason=validated.reason,
            rewrite_hint=validated.rewrite_hint,
            triggered=decision != "allow",
        )
