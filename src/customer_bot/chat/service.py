from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, cast
from uuid import uuid4

from llama_index.core.base.llms.types import ChatMessage

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.config import Settings
from customer_bot.guardrails.service import GuardrailService
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.memory.backend import SessionMemoryBackend


class SupportsAnswer(Protocol):
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
    answer: str
    session_id: str
    trace_id: str | None = None
    status: Literal["answered", "blocked", "handoff", "fallback"] = "answered"
    guardrail_reason: str | None = None
    handoff_required: bool = False
    retry_used: bool = False
    sanitized: bool = False


class ChatService:
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
        resolved_session_id = session_id or str(uuid4())
        history = await self._memory_backend.get_history(resolved_session_id)
        retry_used = False
        sanitized = False

        with self._trace_helper.propagate_trace_attributes(resolved_session_id):
            with self._trace_helper.start_root_observation(
                user_message=user_message,
                session_id=resolved_session_id,
            ) as root:
                trace_id = self._trace_helper.get_current_trace_id()
                if self._guardrail_service is not None:
                    input_result = await self._guardrail_service.evaluate_input(
                        user_message=user_message,
                        chat_history=history,
                        parent_observation=root,
                    )
                    sanitized = sanitized or input_result.sanitized
                    if input_result.action in {"blocked", "handoff"}:
                        answer = input_result.message or self._settings.messages.error_fallback_text
                        await self._append_turn(
                            session_id=resolved_session_id,
                            user_message=input_result.sanitized_user_message,
                            assistant_message=answer,
                            store_raw_user=False,
                        )
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

                agent_result = await self._agent_service.answer(
                    user_message=user_message,
                    chat_history=history,
                    session_id=resolved_session_id,
                    parent_observation=root,
                )

                final_answer = agent_result.answer
                status = "answered"
                guardrail_reason = None
                if self._guardrail_service is not None:
                    output_result = await self._guardrail_service.evaluate_output(
                        user_message=user_message,
                        answer=final_answer,
                        chat_history=history,
                        agent_result=agent_result,
                        parent_observation=root,
                    )
                    sanitized = sanitized or output_result.sanitized
                    if (
                        output_result.action == "rewrite"
                        and self._settings.guardrails.global_.max_output_retries > 0
                    ):
                        rewrite = await self._guardrail_service.rewrite_output(
                            answer=final_answer,
                            rewrite_hint=output_result.rewrite_hint or "Make the answer safer.",
                            user_message=user_message,
                            agent_result=agent_result,
                            parent_observation=root,
                        )
                        retry_used = True
                        final_answer = rewrite.answer
                        output_result = await self._guardrail_service.evaluate_output(
                            user_message=user_message,
                            answer=final_answer,
                            chat_history=history,
                            agent_result=agent_result,
                            parent_observation=root,
                        )
                        sanitized = sanitized or rewrite.sanitized or output_result.sanitized

                    if output_result.action in {"rewrite", "fallback"}:
                        status = "fallback"
                        guardrail_reason = output_result.reason
                        final_answer = self._settings.messages.error_fallback_text

                await self._append_turn(
                    session_id=resolved_session_id,
                    user_message=user_message,
                    assistant_message=final_answer,
                    store_raw_user=True,
                )
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
                self._trace_helper.update_root(
                    root,
                    answer=final_answer,
                    status=result.status,
                    guardrail_reason=result.guardrail_reason,
                    handoff_required=False,
                    retry_used=retry_used,
                    sanitized=sanitized,
                )
                return result

    async def _append_turn(
        self,
        *,
        session_id: str,
        user_message: str,
        assistant_message: str,
        store_raw_user: bool,
    ) -> None:
        stored_user_message = (
            user_message if store_raw_user or user_message != "[redacted]" else "[redacted]"
        )
        await self._memory_backend.append_turn(
            session_id=session_id,
            user_message=ChatMessage(
                role="user",
                content=stored_user_message,
            ),
            assistant_message=ChatMessage(role="assistant", content=assistant_message),
        )
