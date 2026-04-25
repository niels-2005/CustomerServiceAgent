"""Agent orchestration for retrieval-backed customer support answers.

The service builds a LlamaIndex function agent with the configured tools,
captures tracing information around execution, and converts partial failures
into the repository's explicit fallback behavior.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool

from customer_bot.agent.tooling import build_faq_tool, build_product_tool
from customer_bot.agent.tracing import AgentTraceHelper, CollectedEventData
from customer_bot.config import Settings
from customer_bot.model_factory import create_llm
from customer_bot.retrieval.service import FaqRetrieverService, ProductRetrieverService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentAnswerResult:
    """Structured output from one agent run.

    The fields capture the final answer plus execution-side signals that later
    stages use for tracing, guardrails, and fallback decisions.
    """

    answer: str
    tool_calls: list[dict[str, object]] = field(default_factory=list)
    has_tool_error: bool = False
    has_no_match: bool = False
    evidence: list[str] = field(default_factory=list)
    used_history_only: bool = False


class AgentService:
    """Run the support agent and normalize its execution behavior."""

    def __init__(
        self,
        settings: Settings,
        retriever: FaqRetrieverService,
        product_retriever: ProductRetrieverService,
        llm: LLM | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._product_retriever = product_retriever
        self._llm = llm or create_llm(settings)
        self._trace_helper = AgentTraceHelper(settings)

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
        parent_observation: object | None = None,
    ) -> AgentAnswerResult:
        """Answer a user message with tracing-aware agent execution.

        If a parent observation is provided, the caller owns the outer trace
        context. Otherwise this service creates the trace attributes itself.
        """
        agent = self._build_agent()

        trace_context = (
            self._propagate_trace_attributes(session_id)
            if parent_observation is None
            else nullcontext()
        )
        with trace_context:
            with self._start_agent_observation(
                parent_observation=parent_observation,
                user_message=user_message,
                session_id=session_id,
            ) as root:
                collected = CollectedEventData()
                try:
                    handler = agent.run(user_msg=user_message, chat_history=chat_history)
                    collected = await self._trace_helper.collect_event_data(handler, root)
                    result = await handler
                    content = self._resolve_answer_content(
                        result.response, collected.has_tool_error
                    )
                except Exception:
                    # The API contract requires a safe fallback answer instead of
                    # surfacing agent internals to callers.
                    logger.exception("Agent execution failed for session_id=%s", session_id)
                    content = self._settings.messages.error_fallback_text
                    collected.has_tool_error = True

                if root is not None:
                    self._trace_helper.update_agent_observation(root, content, collected)

                return AgentAnswerResult(
                    answer=content,
                    tool_calls=collected.tool_calls,
                    has_tool_error=collected.has_tool_error,
                    has_no_match=collected.has_no_match,
                    evidence=collected.evidence,
                    used_history_only=bool(chat_history) and not collected.tool_calls,
                )

    def _build_agent(self) -> FunctionAgent:
        """Create a fresh function agent configured for one chat turn."""
        return FunctionAgent(
            name="FAQAgent",
            description=self._settings.agent.agent_description,
            system_prompt=self._build_system_prompt(),
            tools=self._build_tools(),
            llm=self._llm,
            streaming=False,
            timeout=self._settings.agent.agent_timeout_seconds,  # ty: ignore[unknown-argument]
        )

    def _resolve_answer_content(self, response: ChatMessage, has_tool_error: bool) -> str:
        """Return the answer content or the configured fallback text."""
        content = (response.content or "").strip()
        if has_tool_error or not content:
            return self._settings.messages.error_fallback_text
        return content

    def _build_system_prompt(self) -> str:
        """Assemble the agent prompt from the configured prompt fragments."""
        prompt_parts = [self._settings.agent.agent_system_prompt.strip()]
        employee_request_instruction = self._settings.messages.employee_request_instruction.strip()
        if employee_request_instruction:
            prompt_parts.append(f"Employee-request guidance: {employee_request_instruction}")
        no_match_instruction = self._settings.messages.no_match_instruction.strip()
        if no_match_instruction:
            prompt_parts.append(f"No-match guidance: {no_match_instruction}")
        return "\n\n".join(part for part in prompt_parts if part)

    def _build_tools(self) -> list[BaseTool | Callable[..., Any]]:
        """Build the retrieval tools exposed to the LlamaIndex agent."""
        return [
            build_faq_tool(
                retriever=self._retriever,
                description=self._settings.messages.faq_tool_description,
            ),
            build_product_tool(
                retriever=self._product_retriever,
                description=self._settings.messages.product_tool_description,
            ),
        ]

    def _start_trace_observation(self, user_message: str, session_id: str):
        return self._trace_helper.start_trace_observation(
            user_message=user_message,
            session_id=session_id,
        )

    def _start_agent_observation(
        self,
        *,
        parent_observation: object | None,
        user_message: str,
        session_id: str,
    ):
        return self._trace_helper.start_agent_observation(
            parent_observation,
            user_message=user_message,
            session_id=session_id,
        )

    def _propagate_trace_attributes(self, session_id: str):
        return self._trace_helper.propagate_trace_attributes(session_id)
