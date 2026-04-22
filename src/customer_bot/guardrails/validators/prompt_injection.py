from __future__ import annotations

from pydantic import BaseModel

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _PromptInjectionDecision(BaseModel):
    decision: str
    score: float
    reason: str
    rewrite_hint: str | None = None


class PromptInjectionGuard:
    def __init__(self, settings: Settings, executor: LlmGuardExecutor) -> None:
        self._settings = settings
        self._executor = executor

    async def check(
        self,
        user_message: str,
        compact_history: str,
        parent_observation=None,
    ) -> GuardrailCheck:
        lowered = user_message.lower()
        if any(
            term.lower() in lowered
            for term in self._settings.guardrails_prompt_injection_heuristic_terms
        ):
            return GuardrailCheck(
                name="prompt_injection",
                decision="block",
                score=1.0,
                reason="Prompt injection heuristic matched.",
                triggered=True,
            )

        prompt = self._settings.guardrails_prompt_injection_user_prompt_template.format(
            user_message=user_message,
            history=compact_history or "-",
        )
        result = await self._executor.run(
            name="prompt_injection",
            system_prompt=self._settings.guardrails_prompt_injection_system_prompt,
            user_prompt=prompt,
            output_model=_PromptInjectionDecision,
            parent_observation=parent_observation,
        )
        validated = _PromptInjectionDecision.model_validate(result.validated_output.model_dump())
        blocked = (
            validated.decision == "block"
            and validated.score >= self._settings.guardrails_prompt_injection_threshold
        )
        return GuardrailCheck(
            name="prompt_injection",
            decision="block" if blocked else "allow",
            score=validated.score,
            reason=validated.reason,
            rewrite_hint=validated.rewrite_hint,
            triggered=blocked,
        )
