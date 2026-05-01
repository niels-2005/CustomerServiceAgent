"""Chat orchestration across memory, guardrails, agent execution, and tracing.

This module owns the high-level flow for a single user turn. It resolves the
session, loads prior history, runs input and output guardrails, records tracing
metadata, and persists the final assistant turn that should be visible in the
session transcript.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol, cast
from uuid import uuid4

from llama_index.core.base.llms.types import ChatMessage

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.config import Settings
from customer_bot.guardrails.service import GuardrailService
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.memory.backend import (
    MemoryBackendError,
    SessionMemoryBackend,
    SessionTurnLimitReachedError,
)

logger = logging.getLogger(__name__)


class SupportsAnswer(Protocol):
    """Protocol for agent backends that can answer a chat turn."""

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
        parent_observation: object | None = None,
    ) -> AgentAnswerResult:
        """Return assistant answer details."""


@dataclass(slots=True)
class ChatResult:
    """Normalized outcome returned by ``ChatService`` for one chat turn."""

    answer: str
    session_id: str
    trace_id: str | None = None
    status: Literal["answered", "blocked", "handoff", "fallback", "session_limit"] = "answered"
    guardrail_reason: str | None = None
    handoff_required: bool = False
    retry_used: bool = False
    sanitized: bool = False


class ChatService:
    """Coordinate a chat turn while preserving session and safety invariants.

    The service keeps route handlers thin by centralizing session resolution,
    guardrail decisions, agent invocation, fallback behavior, memory updates,
    and trace propagation in one place.
    """

    def __init__(
        self,
        memory_backend: SessionMemoryBackend,
        agent_service: SupportsAnswer,
        settings: Settings,
        guardrail_service: GuardrailService | None = None,
    ) -> None:
        self._memory_backend = memory_backend
        self._agent_service = agent_service
        self._settings = settings
        self._guardrail_service = guardrail_service
        self._trace_helper = GuardrailTraceHelper(settings)

    async def chat(self, user_message: str, session_id: str | None = None) -> ChatResult:
        """Process a user message and return the final chat result.

        A new session ID is created when none is supplied. Input guardrails may
        block or hand off before agent execution. Output guardrails may rewrite
        or replace the answer with the configured fallback text.
        """
        resolved_session_id = session_id or str(uuid4())
        retry_used = False
        sanitized = False

        with self._trace_helper.propagate_trace_attributes(resolved_session_id):
            with self._trace_helper.start_root_observation(
                user_message=user_message,
                session_id=resolved_session_id,
            ) as root:
                trace_id = self._trace_helper.get_current_trace_id()
                try:
                    history = await self._memory_backend.get_history(resolved_session_id)

                    if len(history) >= self._settings.memory.max_turns:
                        result = self._build_session_limit_result(
                            session_id=resolved_session_id,
                            trace_id=trace_id,
                        )
                        self._trace_helper.update_root(
                            root,
                            answer=result.answer,
                            status=result.status,
                            guardrail_reason=None,
                            handoff_required=False,
                            retry_used=False,
                            sanitized=False,
                        )
                        return result
                    if self._guardrail_service is not None:
                        try:
                            input_result = await self._guardrail_service.evaluate_input(
                                user_message=user_message,
                                chat_history=history,
                                parent_observation=root,
                            )
                        except Exception:
                            logger.exception(
                                "Input guardrail execution failed for session_id=%s",
                                resolved_session_id,
                            )
                            result = await self._build_fallback_result(
                                session_id=resolved_session_id,
                                trace_id=trace_id,
                                user_message="[redacted]",
                                store_raw_user=False,
                                retry_used=retry_used,
                                sanitized=True,
                            )
                            self._trace_helper.update_root(
                                root,
                                answer=result.answer,
                                status=result.status,
                                guardrail_reason=result.guardrail_reason,
                                handoff_required=result.handoff_required,
                                retry_used=result.retry_used,
                                sanitized=result.sanitized,
                            )
                            return result
                        sanitized = sanitized or input_result.sanitized
                        if input_result.action in {"blocked", "handoff"}:
                            answer = (
                                input_result.message or self._settings.messages.error_fallback_text
                            )
                            limit_reached = await self._append_turn(
                                session_id=resolved_session_id,
                                user_message=input_result.sanitized_user_message,
                                assistant_message=answer,
                                store_raw_user=False,
                            )
                            if limit_reached:
                                result = self._build_session_limit_result(
                                    session_id=resolved_session_id,
                                    trace_id=trace_id,
                                )
                                self._trace_helper.update_root(
                                    root,
                                    answer=result.answer,
                                    status=result.status,
                                    guardrail_reason=None,
                                    handoff_required=False,
                                    retry_used=False,
                                    sanitized=sanitized,
                                )
                                return result
                            result = ChatResult(
                                answer=answer,
                                session_id=resolved_session_id,
                                trace_id=trace_id,
                                status=cast(
                                    Literal["blocked", "handoff"],
                                    input_result.action,
                                ),
                                guardrail_reason=input_result.reason,
                                handoff_required=input_result.action == "handoff",
                                retry_used=False,
                                sanitized=sanitized,
                            )
                            self._trace_helper.update_root(
                                root,
                                answer=answer,
                                status=result.status,
                                guardrail_reason=result.guardrail_reason,
                                handoff_required=result.handoff_required,
                                retry_used=False,
                                sanitized=sanitized,
                            )
                            return result

                    try:
                        agent_result = await self._agent_service.answer(
                            user_message=user_message,
                            chat_history=history,
                            session_id=resolved_session_id,
                            parent_observation=root,
                        )
                    except Exception:
                        logger.exception(
                            "Agent execution raised unexpectedly for session_id=%s",
                            resolved_session_id,
                        )
                        result = await self._build_fallback_result(
                            session_id=resolved_session_id,
                            trace_id=trace_id,
                            user_message=user_message,
                            store_raw_user=True,
                            retry_used=retry_used,
                            sanitized=sanitized,
                        )
                        self._trace_helper.update_root(
                            root,
                            answer=result.answer,
                            status=result.status,
                            guardrail_reason=result.guardrail_reason,
                            handoff_required=result.handoff_required,
                            retry_used=result.retry_used,
                            sanitized=result.sanitized,
                        )
                        return result

                    if agent_result.has_execution_error:
                        result = await self._build_fallback_result(
                            session_id=resolved_session_id,
                            trace_id=trace_id,
                            user_message=user_message,
                            store_raw_user=True,
                            retry_used=retry_used,
                            sanitized=sanitized,
                        )
                        self._trace_helper.update_root(
                            root,
                            answer=result.answer,
                            status=result.status,
                            guardrail_reason=result.guardrail_reason,
                            handoff_required=result.handoff_required,
                            retry_used=result.retry_used,
                            sanitized=result.sanitized,
                        )
                        return result

                    final_answer = agent_result.answer
                    status = "answered"
                    guardrail_reason = None
                    if self._guardrail_service is not None:
                        try:
                            output_result = await self._guardrail_service.evaluate_output(
                                user_message=user_message,
                                answer=final_answer,
                                chat_history=history,
                                agent_result=agent_result,
                                parent_observation=root,
                            )
                        except Exception:
                            logger.exception(
                                "Output guardrail execution failed for session_id=%s",
                                resolved_session_id,
                            )
                            result = await self._build_fallback_result(
                                session_id=resolved_session_id,
                                trace_id=trace_id,
                                user_message=user_message,
                                store_raw_user=True,
                                retry_used=retry_used,
                                sanitized=sanitized,
                            )
                            self._trace_helper.update_root(
                                root,
                                answer=result.answer,
                                status=result.status,
                                guardrail_reason=result.guardrail_reason,
                                handoff_required=result.handoff_required,
                                retry_used=result.retry_used,
                                sanitized=result.sanitized,
                            )
                            return result
                        sanitized = sanitized or output_result.sanitized
                        if (
                            output_result.action == "rewrite"
                            and self._settings.guardrails.global_.max_output_retries > 0
                        ):
                            # A rewritten answer must pass the output checks again before
                            # it can be stored or returned to the client.
                            try:
                                rewrite = await self._guardrail_service.rewrite_output(
                                    answer=final_answer,
                                    rewrite_hint=output_result.rewrite_hint
                                    or "Make the answer safer.",
                                    user_message=user_message,
                                    agent_result=agent_result,
                                    parent_observation=root,
                                )
                            except Exception:
                                logger.exception(
                                    "Output rewrite failed for session_id=%s",
                                    resolved_session_id,
                                )
                                result = await self._build_fallback_result(
                                    session_id=resolved_session_id,
                                    trace_id=trace_id,
                                    user_message=user_message,
                                    store_raw_user=True,
                                    retry_used=retry_used,
                                    sanitized=sanitized,
                                )
                                self._trace_helper.update_root(
                                    root,
                                    answer=result.answer,
                                    status=result.status,
                                    guardrail_reason=result.guardrail_reason,
                                    handoff_required=result.handoff_required,
                                    retry_used=result.retry_used,
                                    sanitized=result.sanitized,
                                )
                                return result
                            retry_used = True
                            final_answer = rewrite.answer
                            try:
                                output_result = await self._guardrail_service.evaluate_output(
                                    user_message=user_message,
                                    answer=final_answer,
                                    chat_history=history,
                                    agent_result=agent_result,
                                    parent_observation=root,
                                )
                            except Exception:
                                logger.exception(
                                    "Output guardrail re-check failed for session_id=%s",
                                    resolved_session_id,
                                )
                                result = await self._build_fallback_result(
                                    session_id=resolved_session_id,
                                    trace_id=trace_id,
                                    user_message=user_message,
                                    store_raw_user=True,
                                    retry_used=retry_used,
                                    sanitized=sanitized or rewrite.sanitized,
                                )
                                self._trace_helper.update_root(
                                    root,
                                    answer=result.answer,
                                    status=result.status,
                                    guardrail_reason=result.guardrail_reason,
                                    handoff_required=result.handoff_required,
                                    retry_used=result.retry_used,
                                    sanitized=result.sanitized,
                                )
                                return result
                            sanitized = sanitized or rewrite.sanitized or output_result.sanitized

                        if output_result.action in {"rewrite", "fallback"}:
                            status = "fallback"
                            guardrail_reason = output_result.reason
                            final_answer = self._settings.messages.error_fallback_text

                    limit_reached = await self._append_turn(
                        session_id=resolved_session_id,
                        user_message=user_message,
                        assistant_message=final_answer,
                        store_raw_user=True,
                    )
                    if limit_reached:
                        result = self._build_session_limit_result(
                            session_id=resolved_session_id,
                            trace_id=trace_id,
                        )
                        self._trace_helper.update_root(
                            root,
                            answer=result.answer,
                            status=result.status,
                            guardrail_reason=None,
                            handoff_required=False,
                            retry_used=retry_used,
                            sanitized=sanitized,
                        )
                        return result
                    result = ChatResult(
                        answer=final_answer,
                        session_id=resolved_session_id,
                        trace_id=trace_id,
                        status=status,
                        guardrail_reason=guardrail_reason,
                        handoff_required=False,
                        retry_used=retry_used,
                        sanitized=sanitized,
                    )
                except MemoryBackendError:
                    result = ChatResult(
                        answer=self._settings.messages.error_fallback_text,
                        session_id=resolved_session_id,
                        trace_id=trace_id,
                        status="fallback",
                        guardrail_reason=None,
                        handoff_required=False,
                        retry_used=retry_used,
                        sanitized=sanitized,
                    )

                self._trace_helper.update_root(
                    root,
                    answer=result.answer,
                    status=result.status,
                    guardrail_reason=result.guardrail_reason,
                    handoff_required=result.handoff_required,
                    retry_used=result.retry_used,
                    sanitized=result.sanitized,
                )
                return result

    async def _append_turn(
        self,
        *,
        session_id: str,
        user_message: str,
        assistant_message: str,
        store_raw_user: bool,
    ) -> bool:
        """Append a user/assistant pair while honoring redaction and limit rules."""
        # Only persist the raw user message when the caller explicitly allows it.
        # Blocked turns may already contain a sanitized placeholder such as
        # ``[redacted]`` and should not re-introduce original sensitive content.
        stored_user_message = (
            user_message if store_raw_user or user_message != "[redacted]" else "[redacted]"
        )
        try:
            await self._memory_backend.append_turn(
                session_id=session_id,
                user_message=ChatMessage(
                    role="user",
                    content=stored_user_message,
                ),
                assistant_message=ChatMessage(role="assistant", content=assistant_message),
            )
        except SessionTurnLimitReachedError:
            return True
        return False

    def _build_session_limit_result(self, *, session_id: str, trace_id: str | None) -> ChatResult:
        """Return the normalized response used when a session reached its turn cap."""
        return ChatResult(
            answer=self._settings.memory.session_limit_text,
            session_id=session_id,
            trace_id=trace_id,
            status="session_limit",
            guardrail_reason=None,
            handoff_required=False,
            retry_used=False,
            sanitized=False,
        )

    async def _build_fallback_result(
        self,
        *,
        session_id: str,
        trace_id: str | None,
        user_message: str,
        store_raw_user: bool,
        retry_used: bool,
        sanitized: bool,
    ) -> ChatResult:
        """Persist and return the normalized technical fallback response."""
        limit_reached = await self._append_turn(
            session_id=session_id,
            user_message=user_message,
            assistant_message=self._settings.messages.error_fallback_text,
            store_raw_user=store_raw_user,
        )
        if limit_reached:
            return self._build_session_limit_result(session_id=session_id, trace_id=trace_id)
        return ChatResult(
            answer=self._settings.messages.error_fallback_text,
            session_id=session_id,
            trace_id=trace_id,
            status="fallback",
            guardrail_reason=None,
            handoff_required=False,
            retry_used=retry_used,
            sanitized=sanitized,
        )
