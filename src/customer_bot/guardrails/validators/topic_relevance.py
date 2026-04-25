"""Topic-relevance guard for filtering out-of-domain requests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _TopicDecision(BaseModel):
    """Structured decision expected from the topic-relevance guard model."""

    decision: Literal["allow", "block"]
    reason: str
    rewrite_hint: str | None = None


class TopicRelevanceGuard:
    """Evaluate whether a request is in scope for the support domain."""

    def __init__(self, settings: Settings, executor: LlmGuardExecutor) -> None:
        self._settings = settings
        self._executor = executor

    async def check(
        self,
        user_message: str,
        compact_history: str,
        parent_observation=None,
    ) -> GuardrailCheck:
        """Run the topic-relevance guard for one user message."""
        prompt = self._settings.guardrails.input.topic_relevance.user_prompt_template.format(
            user_message=user_message,
            history=compact_history or "-",
            allowed_domain_hints=", ".join(
                self._settings.guardrails.input.topic_relevance.allowed_domain_hints
            ),
        )
        result = await self._executor.run(
            name="topic_relevance",
            system_prompt=self._settings.guardrails.input.topic_relevance.system_prompt,
            user_prompt=prompt,
            output_model=_TopicDecision,
            parent_observation=parent_observation,
        )
        validated = _TopicDecision.model_validate(result.validated_output.model_dump())
        blocked = validated.decision == "block"
        return GuardrailCheck(
            name="topic_relevance",
            decision="block" if blocked else "allow",
            reason=validated.reason,
            rewrite_hint=validated.rewrite_hint,
            triggered=blocked,
            decision_source="llm",
            llm_called=True,
        )
