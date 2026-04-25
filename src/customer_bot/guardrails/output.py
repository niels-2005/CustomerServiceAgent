"""Output guard pipeline orchestration.

The pipeline applies answer-time safety checks after agent execution and turns
their combined result into an allow, rewrite, or fallback decision.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.config import Settings
from customer_bot.guardrails.models import GuardrailCheck, GuardrailOutputResult
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.guardrails.validators import BiasGuard, GroundingGuard, OutputSensitiveDataGuard

logger = logging.getLogger(__name__)


class OutputGuardPipeline:
    """Run all configured output guardrails for one candidate answer."""

    def __init__(
        self,
        *,
        settings: Settings,
        trace_helper: GuardrailTraceHelper,
        output_pii_guard: OutputSensitiveDataGuard,
        grounding_guard: GroundingGuard,
        bias_guard: BiasGuard,
    ) -> None:
        self._settings = settings
        self._trace_helper = trace_helper
        self._output_pii_guard = output_pii_guard
        self._grounding_guard = grounding_guard
        self._bias_guard = bias_guard

    async def run(
        self,
        *,
        user_message: str,
        answer: str,
        compact_history: str,
        agent_result: AgentAnswerResult,
        parent_observation: Any | None = None,
    ) -> GuardrailOutputResult:
        """Evaluate output guards and return the final output action."""
        if not self._settings.guardrails.global_.enabled:
            return GuardrailOutputResult(action="allow", reason=None, rewrite_hint=None)

        checks: list[GuardrailCheck] = []
        sanitized = False

        try:
            if self._settings.guardrails.output.pii.enabled:
                # Output PII runs first because it can request a rewrite before
                # more semantic checks evaluate the answer.
                logger.debug("Running output guard: output_sensitive_data")
                blocked, sanitized_answer, pii_check = await self._run_guard(
                    parent_observation=parent_observation,
                    name="output_sensitive_data",
                    payload={"answer": answer},
                    runner_factory=lambda _observation: self._output_pii_guard.check(answer),
                )
                checks.append(pii_check)
                sanitized = sanitized_answer != answer
                logger.info(
                    "Output guard result: name=%s decision=%s triggered=%s",
                    pii_check.name,
                    pii_check.decision,
                    pii_check.triggered,
                )
                if blocked:
                    return GuardrailOutputResult(
                        action="rewrite",
                        reason="output_sensitive_data",
                        rewrite_hint=(
                            "Entferne personenbezogene oder geheime Daten aus der Antwort."
                        ),
                        checks=checks,
                        sanitized=sanitized,
                    )

            tasks = []
            if self._settings.guardrails.output.grounding.enabled:
                logger.debug("Queueing output guard: grounding")
                tasks.append(
                    self._run_guard(
                        parent_observation=parent_observation,
                        name="grounding",
                        payload={
                            "user_message": user_message,
                            "answer": answer,
                            "history": compact_history,
                            "evidence": agent_result.evidence,
                        },
                        runner_factory=lambda observation: self._grounding_guard.check(
                            user_message=user_message,
                            answer=answer,
                            compact_history=compact_history,
                            agent_result=agent_result,
                            parent_observation=observation,
                        ),
                    )
                )
            if self._settings.guardrails.output.bias.enabled:
                logger.debug("Queueing output guard: bias")
                tasks.append(
                    self._run_guard(
                        parent_observation=parent_observation,
                        name="bias",
                        payload={"answer": answer},
                        runner_factory=lambda observation: self._bias_guard.check(
                            answer,
                            parent_observation=observation,
                        ),
                    )
                )
            results = await asyncio.gather(*tasks)
            checks.extend(results)
            for check in results:
                logger.info(
                    "Output guard result: name=%s decision=%s triggered=%s",
                    check.name,
                    check.decision,
                    check.triggered,
                )
        except Exception as exc:
            logger.exception(
                "Output guard pipeline failed: error_type=%s error=%s",
                type(exc).__name__,
                exc,
            )
            if not self._settings.guardrails.global_.fail_closed:
                # In fail-open mode, output guard outages do not replace the
                # answer unless a guard already produced an explicit decision.
                return GuardrailOutputResult(
                    action="allow",
                    reason=None,
                    rewrite_hint=None,
                    checks=checks,
                    sanitized=sanitized,
                )
            return GuardrailOutputResult(
                action="fallback",
                reason="guardrail_error",
                rewrite_hint=None,
                checks=checks,
                sanitized=sanitized,
            )

        for decision in ("fallback", "rewrite"):
            for check in checks:
                if check.decision != decision or not check.triggered:
                    continue
                logger.warning(
                    "Output guard changed response: reason=%s action=%s",
                    check.name,
                    decision,
                )
                return GuardrailOutputResult(
                    action=decision,  # type: ignore[arg-type]
                    reason=check.name,
                    rewrite_hint=check.rewrite_hint,
                    checks=checks,
                    sanitized=sanitized,
                )

        return GuardrailOutputResult(
            action="allow",
            reason=None,
            rewrite_hint=None,
            checks=checks,
            sanitized=sanitized,
        )

    async def _run_guard(
        self,
        *,
        parent_observation: Any | None,
        name: str,
        payload: dict[str, Any],
        runner_factory,
    ):
        """Run one output guard under a traced child observation."""
        with self._trace_helper.start_stage(
            parent_observation,
            name=name,
            input_value=payload,
            metadata={"phase": "output", "guard_name": name},
            as_type="guardrail",
        ) as observation:
            result = await runner_factory(observation)
            if isinstance(result, tuple):
                blocked, sanitized_text, check = result
                self._trace_helper.update_observation(
                    observation,
                    output={
                        "sanitized": sanitized_text != payload.get("answer", ""),
                        "decision_source": check.decision_source,
                        "llm_called": check.llm_called,
                    },
                    metadata={
                        "phase": "output",
                        "guard_name": name,
                        "decision": check.decision,
                        "triggered": check.triggered,
                        "reason": check.reason,
                        "decision_source": check.decision_source,
                        "llm_called": check.llm_called,
                    },
                    level="WARNING" if blocked else None,
                )
                return result
            check = result
            self._trace_helper.update_observation(
                observation,
                output={
                    "decision": check.decision,
                    "triggered": check.triggered,
                    "rewrite_hint": check.rewrite_hint,
                    "decision_source": check.decision_source,
                    "llm_called": check.llm_called,
                },
                metadata={
                    "phase": "output",
                    "guard_name": name,
                    "decision": check.decision,
                    "triggered": check.triggered,
                    "reason": check.reason,
                    "decision_source": check.decision_source,
                    "llm_called": check.llm_called,
                },
                level="WARNING" if check.triggered else None,
            )
            return check
