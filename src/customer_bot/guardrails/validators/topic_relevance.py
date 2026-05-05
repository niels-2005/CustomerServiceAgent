"""Topic-relevance guard for filtering out-of-domain requests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailCheck


class _TopicDecision(BaseModel):
    """Structured decision expected from the topic-relevance guard model."""

    decision: Literal["allow", "block"] = Field(
        description="Whether the request is in scope for the support assistant."
    )


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
        system_prompt = self._settings.guardrails.input.topic_relevance.system_prompt
        allowed_domain_hints = self._settings.guardrails.input.topic_relevance.allowed_domain_hints
        if allowed_domain_hints:
            system_prompt = f"{system_prompt}\nAllowed in-scope domain hints: " + ", ".join(
                allowed_domain_hints
            )
        prompt = self._settings.guardrails.input.topic_relevance.user_prompt_template.format(
            user_message=user_message,
            history=compact_history or "-",
            allowed_domain_hints=", ".join(allowed_domain_hints),
        )
        result = await self._executor.run(
            name="topic_relevance",
            system_prompt=system_prompt,
            user_prompt=prompt,
            output_model=_TopicDecision,
            parent_observation=parent_observation,
        )
        validated = _TopicDecision.model_validate(result.validated_output.model_dump())
        blocked = validated.decision == "block"
        return GuardrailCheck(
            name="topic_relevance",
            decision="block" if blocked else "allow",
            reason=None,
            triggered=blocked,
            decision_source="llm",
            llm_called=True,
        )
