from __future__ import annotations

from pydantic import BaseModel

from customer_bot.config import Settings
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import GuardrailRewriteResult
from customer_bot.guardrails.tracing import GuardrailTraceHelper


class _RewriteOutput(BaseModel):
    answer: str
    reason: str | None = None


class RewriteService:
    def __init__(
        self,
        settings: Settings,
        executor: LlmGuardExecutor,
        trace_helper: GuardrailTraceHelper,
    ) -> None:
        self._settings = settings
        self._executor = executor
        self._trace_helper = trace_helper

    async def rewrite(
        self,
        *,
        answer: str,
        rewrite_hint: str,
        evidence: list[str],
        user_message: str,
        parent_observation=None,
    ) -> GuardrailRewriteResult:
        if not self._settings.guardrails.output.rewrite.enabled:
            return GuardrailRewriteResult(answer=answer)

        prompt = self._settings.guardrails.output.rewrite.user_prompt_template.format(
            answer=answer,
            evidence="\n".join(evidence) or "-",
            rewrite_hint=rewrite_hint,
            user_message=user_message,
        )
        result = await self._executor.run(
            name="rewrite",
            system_prompt=self._settings.guardrails.output.rewrite.system_prompt,
            user_prompt=prompt,
            output_model=_RewriteOutput,
            parent_observation=parent_observation,
        )
        validated = _RewriteOutput.model_validate(result.validated_output.model_dump())
        return GuardrailRewriteResult(answer=validated.answer)
