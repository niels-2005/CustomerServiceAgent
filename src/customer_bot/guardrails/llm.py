from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.model_factory import GuardrailOpenAIClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LlmGuardCall:
    raw_output: str
    validated_output: BaseModel


class LlmGuardExecutor:
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
                raw_output = await self._client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    output_schema=output_model.model_json_schema(),
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

            from guardrails import AsyncGuard

            try:
                guard = AsyncGuard.for_pydantic(output_model, name=name)
                outcome = await guard.validate(raw_output, metadata=metadata)
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
            if not outcome.validation_passed or outcome.validated_output is None:
                error = outcome.error or "Structured guardrail output validation failed."
                logger.warning(
                    "Guardrail validation rejected output: guard=%s model=%s error=%s",
                    name,
                    self._client.model,
                    error,
                )
                self._trace_helper.update_observation(
                    generation,
                    metadata={"guard_name": name, "error": error},
                    level="WARNING",
                    status_message="Guardrail validation rejected output.",
                )
                raise RuntimeError(error)

            validated_output = outcome.validated_output
            if isinstance(validated_output, BaseModel):
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

            try:
                parsed = output_model.model_validate(json.loads(raw_output))
            except Exception as exc:
                logger.exception(
                    "Guardrail JSON parsing failed: guard=%s model=%s error_type=%s error=%s",
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
                    status_message="Guardrail JSON parsing failed.",
                )
                raise
            logger.debug(
                "Guardrail LLM call succeeded: guard=%s model=%s",
                name,
                self._client.model,
            )
            self._trace_helper.update_observation(
                generation,
                output=parsed.model_dump(),
                metadata={"guard_name": name},
            )
            return LlmGuardCall(raw_output=raw_output, validated_output=parsed)
