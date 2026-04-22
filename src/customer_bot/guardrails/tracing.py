from __future__ import annotations

from contextlib import nullcontext
from typing import Any

from langfuse import get_client, propagate_attributes

from customer_bot.config import Settings
from customer_bot.guardrails.sanitization import sanitize_for_tracing


class GuardrailTraceHelper:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def propagate_trace_attributes(self, session_id: str):
        if not self._is_configured():
            return nullcontext()
        return propagate_attributes(
            session_id=session_id,
            trace_name="chat_request",
            tags=["chat", "faq-agent", "guardrails"],
        )

    def start_root_observation(self, *, user_message: str, session_id: str):
        if not self._is_configured():
            return nullcontext(None)

        client = get_client()
        return client.start_as_current_observation(
            name="chat_request",
            as_type="agent",
            input=sanitize_for_tracing({"user_message": user_message}, self._settings),
            metadata={"session_id": session_id, "system_prompt_version": "v1"},
        )

    def start_stage(
        self,
        parent: Any | None,
        *,
        name: str,
        input_value: Any = None,
        metadata: Any = None,
        as_type: str = "span",
        model: str | None = None,
    ):
        if parent is None:
            return nullcontext(None)
        kwargs: dict[str, Any] = {"name": name, "as_type": as_type}
        if input_value is not None:
            kwargs["input"] = sanitize_for_tracing(input_value, self._settings)
        if metadata is not None:
            kwargs["metadata"] = metadata
        if model is not None:
            kwargs["model"] = model
        if hasattr(parent, "start_as_current_observation"):
            return parent.start_as_current_observation(**kwargs)
        return nullcontext(parent.start_observation(**kwargs))

    def update_observation(
        self,
        observation: Any | None,
        *,
        output: Any = None,
        metadata: Any = None,
        level: str | None = None,
        status_message: str | None = None,
    ) -> None:
        if observation is None:
            return
        kwargs: dict[str, Any] = {}
        if output is not None:
            kwargs["output"] = sanitize_for_tracing(output, self._settings)
        if metadata is not None:
            kwargs["metadata"] = metadata
        if level is not None:
            kwargs["level"] = level
        if status_message is not None:
            kwargs["status_message"] = status_message
        observation.update(**kwargs)

    def update_root(
        self,
        root: Any | None,
        *,
        answer: str,
        status: str,
        guardrail_reason: str | None,
        handoff_required: bool,
        retry_used: bool,
        sanitized: bool,
    ) -> None:
        if root is None:
            return
        root.update(
            output=sanitize_for_tracing({"answer": answer}, self._settings),
            metadata={
                "status": status,
                "guardrail_reason": guardrail_reason,
                "handoff_required": handoff_required,
                "retry_used": retry_used,
                "sanitized": sanitized,
            },
        )

    def _is_configured(self) -> bool:
        return bool(self._settings.langfuse_public_key and self._settings.langfuse_secret_key)
