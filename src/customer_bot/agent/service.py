from __future__ import annotations

import logging

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.llms.llm import LLM
from llama_index.core.tools import FunctionTool

from customer_bot.agent.tooling import build_faq_tool
from customer_bot.agent.tracing import AgentTraceHelper, CollectedEventData
from customer_bot.config import Settings
from customer_bot.model_factory import create_llm
from customer_bot.retrieval.service import FaqRetrieverService

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(
        self,
        settings: Settings,
        retriever: FaqRetrieverService,
        llm: LLM | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._llm = llm or create_llm(settings)
        self._trace_helper = AgentTraceHelper(settings)

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
    ) -> str:
        agent = self._build_agent()

        with self._propagate_trace_attributes(session_id):
            with self._start_trace_observation(
                user_message=user_message, session_id=session_id
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
                    logger.exception("Agent execution failed for session_id=%s", session_id)
                    content = self._settings.error_fallback_text
                    collected.has_tool_error = True

                if root is not None:
                    self._trace_helper.update_root_observation(root, content, collected)

                return content

    def _build_agent(self) -> FunctionAgent:
        return FunctionAgent(
            name="FAQAgent",
            description=self._settings.agent_description,
            system_prompt=self._build_system_prompt(),
            tools=[self._build_tool()],
            llm=self._llm,
            streaming=False,
            timeout=self._settings.agent_timeout_seconds,  # ty: ignore[unknown-argument]
        )

    def _resolve_answer_content(self, response: ChatMessage, has_tool_error: bool) -> str:
        content = (response.content or "").strip()
        if has_tool_error or not content:
            return self._settings.error_fallback_text
        return content

    def _build_system_prompt(self) -> str:
        prompt_parts = [self._settings.agent_system_prompt.strip()]
        no_match_instruction = self._settings.no_match_instruction.strip()
        if no_match_instruction:
            prompt_parts.append(f"No-match guidance: {no_match_instruction}")
        return "\n\n".join(part for part in prompt_parts if part)

    def _build_tool(self) -> FunctionTool:
        return build_faq_tool(
            retriever=self._retriever,
            description=self._settings.faq_tool_description,
        )

    def _start_trace_observation(self, user_message: str, session_id: str):
        return self._trace_helper.start_trace_observation(
            user_message=user_message,
            session_id=session_id,
        )

    def _propagate_trace_attributes(self, session_id: str):
        return self._trace_helper.propagate_trace_attributes(session_id)
