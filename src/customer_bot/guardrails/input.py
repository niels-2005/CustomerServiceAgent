"""Input guard pipeline orchestration.

The pipeline runs input-time safety checks, preserves their ordering semantics,
and converts the collected guard results into one normalized action.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from llama_index.core.base.llms.types import ChatMessage

from customer_bot.config import Settings
from customer_bot.guardrails.models import GuardrailCheck, GuardrailInputResult
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.guardrails.validators import (
    EscalationGuard,
    PromptInjectionGuard,
    SecretPIIGuard,
    TopicRelevanceGuard,
)

logger = logging.getLogger(__name__)


class InputGuardPipeline:
    """Run all configured input guardrails for one user message."""

    def __init__(
        self,
        *,
        settings: Settings,
        trace_helper: GuardrailTraceHelper,
        pii_guard: SecretPIIGuard,
        prompt_injection_guard: PromptInjectionGuard,
        topic_relevance_guard: TopicRelevanceGuard,
        escalation_guard: EscalationGuard,
    ) -> None:
        self._settings = settings
        self._trace_helper = trace_helper
        self._pii_guard = pii_guard
        self._prompt_injection_guard = prompt_injection_guard
        self._topic_relevance_guard = topic_relevance_guard
        self._escalation_guard = escalation_guard

    async def run(
        self,
        *,
        user_message: str,
        chat_history: list[ChatMessage],
        parent_observation: Any | None = None,
    ) -> GuardrailInputResult:
        """Evaluate input guards and return the first blocking decision, if any."""
        if not self._settings.guardrails.global_.enabled:
            return GuardrailInputResult(
                action="allow",
                reason=None,
                message=None,
                sanitized_user_message=user_message,
            )

        compact_history = self._compact_history(chat_history)
        checks: list[GuardrailCheck] = []
        sanitized_user_message = user_message

        try:
            if self._settings.guardrails.input.pii.enabled:
                # PII runs first because it can sanitize the message before any
                # later guard or trace sees it.
                blocked, sanitized_user_message, pii_check = await self._run_guard(
                    parent_observation=parent_observation,
                    name="secret_pii",
                    payload={"user_message": user_message},
                    runner_factory=lambda _observation: self._pii_guard.check(user_message),
                )
                checks.append(pii_check)
                logger.info(
                    "Input guard result: name=%s decision=%s triggered=%s",
                    pii_check.name,
                    pii_check.decision,
                    pii_check.triggered,
                )
                if blocked:
                    return GuardrailInputResult(
                        action="blocked",
                        reason="secret_pii",
                        message=self._settings.guardrails.input.pii.message,
                        sanitized_user_message=sanitized_user_message,
                        checks=checks,
                        sanitized=sanitized_user_message != user_message,
                    )

            tasks = []
            if self._settings.guardrails.input.prompt_injection.enabled:
                logger.debug("Queueing input guard: prompt_injection")
                tasks.append(
                    self._run_guard(
                        parent_observation=parent_observation,
                        name="prompt_injection",
                        payload={"user_message": user_message, "history": compact_history},
                        runner_factory=lambda observation: self._prompt_injection_guard.check(
                            user_message,
                            compact_history,
                            parent_observation=observation,
                        ),
                    )
                )
            if self._settings.guardrails.input.topic_relevance.enabled:
                logger.debug("Queueing input guard: topic_relevance")
                tasks.append(
                    self._run_guard(
                        parent_observation=parent_observation,
                        name="topic_relevance",
                        payload={"user_message": user_message, "history": compact_history},
                        runner_factory=lambda observation: self._topic_relevance_guard.check(
                            user_message,
                            compact_history,
                            parent_observation=observation,
                        ),
                    )
                )
            if self._settings.guardrails.input.escalation.enabled:
                logger.debug("Queueing input guard: escalation")
                tasks.append(
                    self._run_guard(
                        parent_observation=parent_observation,
                        name="escalation",
                        payload={"user_message": user_message, "history": compact_history},
                        runner_factory=lambda observation: self._escalation_guard.check(
                            user_message,
                            compact_history,
                            parent_observation=observation,
                        ),
                    )
                )
            results = await asyncio.gather(*tasks)
            checks.extend(results)
            for check in results:
                logger.info(
                    "Input guard result: name=%s decision=%s triggered=%s",
                    check.name,
                    check.decision,
                    check.triggered,
                )
        except Exception as exc:
            logger.exception(
                "Input guard pipeline failed: error_type=%s error=%s",
                type(exc).__name__,
                exc,
            )
            if not self._settings.guardrails.global_.fail_closed:
                # In fail-open mode, guardrail outages do not block customer
                # traffic, but the partial check results are still returned.
                return GuardrailInputResult(
                    action="allow",
                    reason=None,
                    message=None,
                    sanitized_user_message=sanitized_user_message,
                    checks=checks,
                )
            return GuardrailInputResult(
                action="blocked",
                reason="guardrail_error",
                message=self._settings.messages.error_fallback_text,
                sanitized_user_message=sanitized_user_message,
                checks=checks,
                sanitized=sanitized_user_message != user_message,
            )

        for name, action, message in (
            (
                "prompt_injection",
                "blocked",
                self._settings.guardrails.input.prompt_injection.message,
            ),
            (
                "topic_relevance",
                "blocked",
                self._settings.guardrails.input.topic_relevance.message,
            ),
            ("escalation", "handoff", self._settings.guardrails.input.escalation.message),
        ):
            check = next((item for item in checks if item.name == name and item.triggered), None)
            if check is None:
                continue
            response_message = message
            if (
                name == "topic_relevance"
                and self._settings.guardrails.input.topic_relevance.help_text
            ):
                response_message = (
                    f"{message} {self._settings.guardrails.input.topic_relevance.help_text}".strip()
                )
            logger.warning(
                "Input guard blocked request: reason=%s action=%s",
                name if name != "topic_relevance" else "off_topic",
                action,
            )
            return GuardrailInputResult(
                action=action,  # type: ignore[arg-type]
                reason=name if name != "topic_relevance" else "off_topic",
                message=response_message,
                sanitized_user_message=sanitized_user_message,
                checks=checks,
                sanitized=sanitized_user_message != user_message,
            )

        return GuardrailInputResult(
            action="allow",
            reason=None,
            message=None,
            sanitized_user_message=sanitized_user_message,
            checks=checks,
            sanitized=sanitized_user_message != user_message,
        )

    async def _run_guard(
        self,
        *,
        parent_observation: Any | None,
        name: str,
        payload: dict[str, Any],
        runner_factory,
    ):
        """Run one guard under a traced child observation."""
        with self._trace_helper.start_stage(
            parent_observation,
            name=name,
            input_value=payload,
            metadata={"phase": "input", "guard_name": name},
            as_type="guardrail",
        ) as observation:
            result = await runner_factory(observation)
            if isinstance(result, tuple):
                blocked, sanitized_text, check = result
                self._trace_helper.update_observation(
                    observation,
                    output={
                        "sanitized": sanitized_text != payload.get("user_message", ""),
                        "decision_source": check.decision_source,
                        "llm_called": check.llm_called,
                    },
                    metadata={
                        "phase": "input",
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
                    "decision_source": check.decision_source,
                    "llm_called": check.llm_called,
                },
                metadata={
                    "phase": "input",
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

    @staticmethod
    def _compact_history(chat_history: list[ChatMessage]) -> str:
        """Reduce recent chat history to the small context window guards need."""
        snippets = []
        for message in chat_history[-4:]:
            content = (message.content or "").strip()
            if not content:
                continue
            snippets.append(f"{message.role}: {content}")
        return "\n".join(snippets)
