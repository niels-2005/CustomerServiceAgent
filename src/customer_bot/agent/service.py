from __future__ import annotations

import asyncio
from contextlib import nullcontext
from typing import Any

from langfuse import get_client
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentOutput
from llama_index.core.base.llms.types import ChatMessage, ThinkingBlock
from llama_index.core.llms.llm import LLM
from llama_index.core.tools import FunctionTool

from customer_bot.config import Settings
from customer_bot.llama import create_llm
from customer_bot.retrieval.service import FaqRetrieverService

FAQ_TOOL_NAME = "faq_lookup"


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

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
    ) -> str:
        tool = self._build_tool()
        agent = FunctionAgent(
            name="FAQAgent",
            description="Agent for FAQ-only customer support responses",
            system_prompt=(
                "You are a customer support FAQ assistant. "
                "Always call the faq_lookup tool with the user question and "
                "return the tool output exactly as-is."
            ),
            tools=[tool],
            llm=self._llm,
            streaming=False,
        )

        with self._start_trace_observation(
            user_message=user_message, session_id=session_id
        ) as root:
            handler = agent.run(user_msg=user_message, chat_history=chat_history)
            thinking = await self._collect_thinking_from_events(handler)
            result = await handler

            content = (result.response.content or "").strip()
            if not content:
                content = self._settings.fallback_text

            if root is not None:
                root.update(output={"answer": content, "thinking": thinking or ""})

            return content

    def _build_tool(self) -> FunctionTool:
        async def faq_lookup(question: str) -> str:
            retrieval_result = await asyncio.to_thread(
                self._retriever.retrieve_best_answer, question
            )
            if retrieval_result.answer is None:
                return self._settings.fallback_text
            return retrieval_result.answer or self._settings.fallback_text

        return FunctionTool.from_defaults(
            fn=faq_lookup,
            name=FAQ_TOOL_NAME,
            description=(
                "Find the best matching FAQ answer for a user question. "
                "Returns a plain German answer string."
            ),
            return_direct=True,
        )

    def _start_trace_observation(self, user_message: str, session_id: str):
        if not self._settings.langfuse_public_key or not self._settings.langfuse_secret_key:
            return nullcontext(None)

        langfuse = get_client()
        return langfuse.start_as_current_observation(
            name="chat_request",
            as_type="agent",
            input={"user_message": user_message, "session_id": session_id},
        )

    async def _collect_thinking_from_events(self, handler: Any) -> str | None:
        thinking: str | None = None
        async for event in handler.stream_events():
            if isinstance(event, AgentOutput):
                event_thinking = self._extract_thinking(event.raw, event.response)
                if event_thinking:
                    thinking = event_thinking
        return thinking

    @staticmethod
    def _extract_thinking(raw: Any, response: ChatMessage) -> str | None:
        if isinstance(raw, dict):
            message = raw.get("message")
            if isinstance(message, dict):
                thinking = message.get("thinking")
                if isinstance(thinking, str) and thinking.strip():
                    return thinking

        for block in response.blocks:
            if isinstance(block, ThinkingBlock) and block.content and block.content.strip():
                return block.content

        return None
