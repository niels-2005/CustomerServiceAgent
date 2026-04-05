from __future__ import annotations

import asyncio
import json
from contextlib import nullcontext
from typing import Any

from langfuse import get_client, propagate_attributes
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentOutput, ToolCallResult
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
            with self._propagate_session(session_id):
                handler = agent.run(user_msg=user_message, chat_history=chat_history)
                thinking, tool_calls = await self._collect_event_data(handler)
                result = await handler

            content = (result.response.content or "").strip()
            if not content:
                content = self._settings.fallback_text

            if root is not None:
                root.update(
                    output={
                        "answer": content,
                        "thinking": thinking or "",
                        "tool_calls": tool_calls,
                    }
                )

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
        if not self._is_langfuse_configured():
            return nullcontext(None)

        langfuse = get_client()
        return langfuse.start_as_current_observation(
            name="chat_request",
            as_type="agent",
            input={"user_message": user_message, "session_id": session_id},
        )

    def _propagate_session(self, session_id: str):
        if not self._is_langfuse_configured():
            return nullcontext()
        return propagate_attributes(session_id=session_id)

    def _is_langfuse_configured(self) -> bool:
        return bool(self._settings.langfuse_public_key and self._settings.langfuse_secret_key)

    async def _collect_event_data(self, handler: Any) -> tuple[str | None, list[dict[str, Any]]]:
        thinking: str | None = None
        tool_calls: list[dict[str, Any]] = []
        async for event in handler.stream_events():
            if isinstance(event, AgentOutput):
                event_thinking = self._extract_thinking(event.raw, event.response)
                if event_thinking:
                    thinking = event_thinking
            elif isinstance(event, ToolCallResult):
                tool_calls.append(self._serialize_tool_call(event))

        return thinking, tool_calls

    def _serialize_tool_call(self, event: ToolCallResult) -> dict[str, Any]:
        return {
            "tool_name": event.tool_name,
            "tool_input": self._json_friendly(event.tool_kwargs),
            "tool_output": self._normalize_tool_output(event),
            "is_error": event.tool_output.is_error,
        }

    def _normalize_tool_output(self, event: ToolCallResult) -> Any:
        content = event.tool_output.content
        if isinstance(content, str) and content.strip():
            return content
        if content:
            return self._json_friendly(content)

        raw_output = event.tool_output.raw_output
        if raw_output is None:
            return None

        return self._json_friendly(raw_output)

    @staticmethod
    def _json_friendly(value: Any) -> Any:
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            return str(value)
        return value

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
