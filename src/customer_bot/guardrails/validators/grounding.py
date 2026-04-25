from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _GroundingDecision(BaseModel):
    decision: Literal["allow", "rewrite", "fallback"]
    reason: str
    rewrite_hint: str | None = None


class GroundingGuard:
    def __init__(self, settings: Settings, executor: LlmGuardExecutor) -> None:
        self._settings = settings
        self._executor = executor

    async def check(
        self,
        *,
        user_message: str,
        answer: str,
        compact_history: str,
        agent_result: AgentAnswerResult,
        parent_observation=None,
    ) -> GuardrailCheck:
        no_tool_answer = not agent_result.tool_calls and not agent_result.used_history_only
        if agent_result.has_tool_error:
            return GuardrailCheck(
                name="grounding",
                decision="fallback",
                reason="Agent reported a tool error.",
                triggered=True,
            )
        if not agent_result.evidence and not agent_result.used_history_only and not no_tool_answer:
            return GuardrailCheck(
                name="grounding",
                decision="fallback",
                reason="No grounding evidence available.",
                triggered=True,
            )

        prompt = self._settings.guardrails.output.grounding.user_prompt_template.format(
            user_message=user_message,
            answer=answer,
            evidence="\n".join(agent_result.evidence) or "-",
            history=compact_history or "-",
            has_tool_error=str(agent_result.has_tool_error).lower(),
            used_history_only=str(agent_result.used_history_only).lower(),
            no_tool_answer=str(no_tool_answer).lower(),
            tool_call_count=len(agent_result.tool_calls),
        )
        result = await self._executor.run(
            name="grounding",
            system_prompt=self._settings.guardrails.output.grounding.system_prompt,
            user_prompt=prompt,
            output_model=_GroundingDecision,
            metadata={"sources": agent_result.evidence},
            parent_observation=parent_observation,
        )
        validated = _GroundingDecision.model_validate(result.validated_output.model_dump())
        decision = validated.decision
        if decision == "fallback" and self._reason_supports_answer(validated.reason):
            decision = "allow"
        return GuardrailCheck(
            name="grounding",
            decision=decision,
            reason=validated.reason,
            rewrite_hint=validated.rewrite_hint,
            triggered=decision != "allow",
        )

    @staticmethod
    def _reason_supports_answer(reason: str) -> bool:
        lowered = reason.lower()
        positive_markers = (
            "directly matches",
            "directly supported",
            "matches the evidence",
            "supported by the evidence",
            "grounded in the evidence",
        )
        return any(marker in lowered for marker in positive_markers)
