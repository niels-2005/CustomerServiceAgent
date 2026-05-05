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

from customer_bot.agent.tooling import (
    SupportsFaqRetrieval,
    SupportsProductRetrieval,
    build_faq_tool,
    build_product_tool,
)
from customer_bot.agent.tracing import AgentTraceHelper, CollectedEventData
from customer_bot.config import Settings
from customer_bot.model_factory import create_llm
from customer_bot.retrieval.types import RetrievalPrefetchContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentAnswerResult:
    """Structured output from one agent run.

    The fields capture the final answer plus execution-side signals that later
    stages use for tracing, guardrails, and fallback decisions.
    """

    answer: str
    tool_calls: list[dict[str, object]] = field(default_factory=list)
    has_execution_error: bool = False
    has_no_match: bool = False
    evidence: list[str] = field(default_factory=list)
    used_history_only: bool = False
    prefetch_used: bool = False
    prefetch_sources: list[str] = field(default_factory=list)

    @property
    def has_tool_error(self) -> bool:
        """Backward-compatible alias for older guardrail and test call sites."""
        return self.has_execution_error


class AgentService:
    """Run the support agent and normalize its execution behavior."""

    def __init__(
        self,
        settings: Settings,
        retriever: SupportsFaqRetrieval,
        product_retriever: SupportsProductRetrieval,
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
        prefetch_context: RetrievalPrefetchContext | None = None,
        parent_observation: object | None = None,
    ) -> AgentAnswerResult:
        """Answer a user message with tracing-aware agent execution.

        If a parent observation is provided, the caller owns the outer trace
        context. Otherwise this service creates the trace attributes itself.
        """
        system_prompt = self._build_system_prompt(prefetch_context=prefetch_context)
        agent = self._build_agent(system_prompt=system_prompt)

        trace_context = (
            self._propagate_trace_attributes(session_id)
            if parent_observation is None
            else nullcontext()
        )
        with trace_context:
            with self._start_agent_observation(
                parent_observation=parent_observation,
                system_prompt=system_prompt,
                user_message=user_message,
                chat_history=chat_history,
                session_id=session_id,
            ) as root:
                collected = CollectedEventData()
                try:
                    handler = agent.run(user_msg=user_message, chat_history=chat_history)
                    collected = await self._trace_helper.collect_event_data(handler, root)
                    result = await handler
                    content = self._resolve_answer_content(
                        result.response, collected.has_execution_error
                    )
                except Exception:
                    # The API contract requires a safe fallback answer instead of
                    # surfacing agent internals to callers.
                    logger.exception("Agent execution failed for session_id=%s", session_id)
                    content = self._settings.messages.error_fallback_text
                    collected.has_execution_error = True

                if root is not None:
                    self._trace_helper.update_agent_observation(root, content, collected)

                return AgentAnswerResult(
                    answer=content,
                    tool_calls=collected.tool_calls,
                    has_execution_error=collected.has_execution_error,
                    has_no_match=collected.has_no_match,
                    evidence=collected.evidence,
                    used_history_only=bool(chat_history) and not collected.tool_calls,
                    prefetch_used=bool(prefetch_context and prefetch_context.has_hits),
                    prefetch_sources=list(prefetch_context.sources) if prefetch_context else [],
                )

    async def warm_up(self, *, user_message: str) -> None:
        """Run one synthetic turn to pre-load agent-side resources."""
        agent = self._build_agent(system_prompt=self._build_system_prompt())
        handler = agent.run(user_msg=user_message, chat_history=[])
        await handler

    def _build_agent(self, *, system_prompt: str) -> FunctionAgent:
        """Create a fresh function agent configured for one chat turn."""
        return FunctionAgent(
            name="FAQAgent",
            description=self._settings.agent.agent_description,
            system_prompt=system_prompt,
            tools=self._build_tools(),
            llm=self._llm,
            streaming=False,
            timeout=self._settings.agent.agent_timeout_seconds,  # ty: ignore[unknown-argument]
        )

    def _resolve_answer_content(self, response: ChatMessage, has_execution_error: bool) -> str:
        """Return the answer content or the configured fallback text."""
        content = (response.content or "").strip()
        if has_execution_error or not content:
            return self._settings.messages.error_fallback_text
        return content

    def _build_system_prompt(
        self, *, prefetch_context: RetrievalPrefetchContext | None = None
    ) -> str:
        """Assemble the agent prompt from the configured prompt fragments."""
        prompt_parts = [self._settings.agent.agent_system_prompt.strip()]
        prefetch_context_instruction = self._settings.agent.prefetch_context_instruction.strip()
        if prefetch_context_instruction:
            prompt_parts.append(f"Prefetch guidance: {prefetch_context_instruction}")
        prefetch_no_repeat_instruction = self._settings.agent.prefetch_no_repeat_instruction.strip()
        if prefetch_no_repeat_instruction:
            prompt_parts.append(f"Prefetch no-repeat guidance: {prefetch_no_repeat_instruction}")
        employee_request_instruction = self._settings.messages.employee_request_instruction.strip()
        if employee_request_instruction:
            prompt_parts.append(f"Employee-request guidance: {employee_request_instruction}")
        no_match_instruction = self._settings.messages.no_match_instruction.strip()
        if no_match_instruction:
            prompt_parts.append(f"No-match guidance: {no_match_instruction}")
        prefetch_section = self._render_prefetch_context(prefetch_context)
        if prefetch_section:
            prompt_parts.append(prefetch_section)
        return "\n\n".join(part for part in prompt_parts if part)

    def _render_prefetch_context(self, prefetch_context: RetrievalPrefetchContext | None) -> str:
        """Render deterministic retrieval context into a compact prompt section."""
        if prefetch_context is None:
            return ""

        lines = [
            "Deterministic prefetch context for this request:",
            f"- query: {prefetch_context.query}",
        ]
        if prefetch_context.faq_hits:
            lines.append("- faq matches:")
            for hit in prefetch_context.faq_hits[:3]:
                lines.append(f"  - {hit.faq_id}: {hit.answer}")
        if prefetch_context.product_hits:
            lines.append("- product matches:")
            for hit in prefetch_context.product_hits[:3]:
                details = [hit.name, hit.description]
                extra_bits = [
                    bit
                    for bit in (
                        f"category={hit.category}" if hit.category else "",
                        f"price={hit.price} {hit.currency}".strip() if hit.price else "",
                        f"availability={hit.availability}" if hit.availability else "",
                        f"features={hit.features}" if hit.features else "",
                        f"url={hit.url}" if hit.url else "",
                    )
                    if bit
                ]
                detail_text = " | ".join([bit for bit in details if bit] + extra_bits)
                lines.append(f"  - {hit.product_id}: {detail_text}")
        if prefetch_context.failed_sources:
            lines.append(
                "- prefetch warnings: "
                + ", ".join(sorted(prefetch_context.failed_sources))
                + " retrieval unavailable during prefetch"
            )
        if not prefetch_context.has_hits:
            lines.append("- no deterministic matches were found")
        return "\n".join(lines)

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
        """Delegate root trace creation to the tracing helper."""
        return self._trace_helper.start_trace_observation(
            user_message=user_message,
            session_id=session_id,
        )

    def _start_agent_observation(
        self,
        *,
        parent_observation: object | None,
        system_prompt: str,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
    ):
        """Delegate agent observation creation to the tracing helper."""
        return self._trace_helper.start_agent_observation(
            parent_observation,
            system_prompt=system_prompt,
            user_message=user_message,
            chat_history=chat_history,
            session_id=session_id,
        )

    def _propagate_trace_attributes(self, session_id: str):
        """Delegate trace attribute propagation to the tracing helper."""
        return self._trace_helper.propagate_trace_attributes(session_id)
