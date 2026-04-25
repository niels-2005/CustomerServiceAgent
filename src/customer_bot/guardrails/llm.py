"""LLM-backed execution helper for structured guardrail decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.model_factory import GuardrailOpenAIClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LlmGuardCall:
    """Raw and validated output from one guardrail LLM invocation."""

    raw_output: str
    validated_output: BaseModel


class LlmGuardExecutor:
    """Execute structured guardrail prompts with tracing and validation."""

    def __init__(
        self,
        client: GuardrailOpenAIClient | None,
        trace_helper: GuardrailTraceHelper,
    ) -> None:
        self._client = client
        self._trace_helper = trace_helper

    async def run(
        self,
        *,
        name: str,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
        metadata: dict[str, Any] | None = None,
        parent_observation: Any | None = None,
    ) -> LlmGuardCall:
        """Run one guardrail LLM call and return the validated result."""
        if self._client is None:
            raise RuntimeError(f"Guardrail LLM client is unavailable for {name}.")

        with self._trace_helper.start_stage(
            parent_observation,
            name=f"{name}_llm",
            input_value={
                "guard_name": name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            },
            metadata={"guard_name": name},
            as_type="generation",
            model=self._client.model,
        ) as generation:
            logger.debug(
                "Starting guardrail LLM call: guard=%s model=%s",
                name,
                self._client.model,
            )
            try:
                validated_output = await self._client.complete_structured(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    output_model=output_model,
                )
            except Exception as exc:
                logger.exception(
                    "Guardrail OpenAI call failed: guard=%s model=%s error_type=%s error=%s",
                    name,
                    self._client.model,
                    type(exc).__name__,
                    exc,
                )
                self._trace_helper.update_observation(
                    generation,
                    metadata={
                        "guard_name": name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    level="ERROR",
                    status_message="Guardrail LLM request failed.",
                )
                raise

            try:
                validated_output = output_model.model_validate(validated_output.model_dump())
                raw_output = validated_output.model_dump_json()
            except Exception as exc:
                logger.exception(
                    (
                        "Guardrail structured validation failed: "
                        "guard=%s model=%s error_type=%s error=%s"
                    ),
                    name,
                    self._client.model,
                    type(exc).__name__,
                    exc,
                )
                self._trace_helper.update_observation(
                    generation,
                    metadata={
                        "guard_name": name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    level="ERROR",
                    status_message="Guardrail structured validation failed.",
                )
                raise
            logger.debug(
                "Guardrail LLM call succeeded: guard=%s model=%s",
                name,
                self._client.model,
            )
            self._trace_helper.update_observation(
                generation,
                output=validated_output.model_dump(),
                metadata={"guard_name": name},
            )
            return LlmGuardCall(raw_output=raw_output, validated_output=validated_output)
