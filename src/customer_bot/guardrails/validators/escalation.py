"""Escalation guard for employee-request and handoff detection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _EscalationDecision(BaseModel):
    """Structured decision expected from the escalation guard model."""

    decision: Literal["allow", "handoff"] = Field(
        description="Whether the request can continue with the bot or needs human handoff."
    )
    reason: str = Field(description="Short explanation of the escalation decision.")


class EscalationGuard:
    """Evaluate whether the conversation should be handed off."""

    def __init__(self, settings: Settings, executor: LlmGuardExecutor) -> None:
        self._settings = settings
        self._executor = executor

    async def check(
        self,
        user_message: str,
        compact_history: str,
        parent_observation=None,
    ) -> GuardrailCheck:
        """Run heuristic and LLM-based escalation checks."""
        lowered = f"{compact_history}\n{user_message}".lower()
        if any(
            term.lower() in lowered
            for term in self._settings.guardrails.input.escalation.heuristic_terms
        ):
            return GuardrailCheck(
                name="escalation",
                decision="handoff",
                reason="Escalation heuristic matched.",
                triggered=True,
                decision_source="heuristic",
                llm_called=False,
            )

        prompt = self._settings.guardrails.input.escalation.user_prompt_template.format(
            user_message=user_message,
            history=compact_history or "-",
            escalation_terms=", ".join(self._settings.guardrails.input.escalation.heuristic_terms),
        )
        result = await self._executor.run(
            name="escalation",
            system_prompt=self._settings.guardrails.input.escalation.system_prompt,
            user_prompt=prompt,
            output_model=_EscalationDecision,
            parent_observation=parent_observation,
        )
        validated = _EscalationDecision.model_validate(result.validated_output.model_dump())
        handoff = validated.decision == "handoff"
        return GuardrailCheck(
            name="escalation",
            decision="handoff" if handoff else "allow",
            reason=validated.reason,
            triggered=handoff,
            decision_source="llm",
            llm_called=True,
        )
