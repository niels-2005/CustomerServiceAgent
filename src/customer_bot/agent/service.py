from __future__ import annotations

import asyncio
import json
import logging
from contextlib import nullcontext
from typing import Any

from langfuse import get_client, propagate_attributes
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentOutput, ToolCallResult
from llama_index.core.base.llms.types import ChatMessage, ThinkingBlock
from llama_index.core.llms.llm import LLM
from llama_index.core.tools import FunctionTool
from pydantic import BaseModel, Field

from customer_bot.config import Settings
from customer_bot.llama import create_llm
from customer_bot.retrieval.service import FaqRetrieverService
from customer_bot.retrieval.types import RetrievalHit

FAQ_TOOL_NAME = "faq_lookup"
logger = logging.getLogger(__name__)


class FaqLookupInput(BaseModel):
    question: str = Field(description="User question to look up in the FAQ corpus.")


class FaqLookupMatch(BaseModel):
    faq_id: str = Field(description="FAQ identifier of a matched entry.")
    answer: str = Field(description="FAQ answer text for the matched entry.")
    score: float | None = Field(
        default=None,
        description="Similarity score of the matched entry, when available.",
    )


class FaqLookupOutput(BaseModel):
    matches: list[FaqLookupMatch] = Field(
        default_factory=list,
        description="Ranked FAQ matches after similarity filtering.",
    )


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
            description=self._settings.agent_description,
            system_prompt=self._build_system_prompt(),
            tools=[tool],
            llm=self._llm,
            streaming=False,
            timeout=self._settings.agent_timeout_seconds,
        )

        with self._start_trace_observation(
            user_message=user_message, session_id=session_id
        ) as root:
            thinking: str | None = None
            tool_calls: list[dict[str, Any]] = []
            with self._propagate_session(session_id):
                try:
                    handler = agent.run(user_msg=user_message, chat_history=chat_history)
                    thinking, tool_calls, has_tool_error = await self._collect_event_data(handler)
                    result = await handler
                    content = (result.response.content or "").strip()
                    if has_tool_error or not content:
                        content = self._settings.error_fallback_text
                except Exception:
                    logger.exception("Agent execution failed for session_id=%s", session_id)
                    content = self._settings.error_fallback_text

            if root is not None:
                root.update(
                    output={
                        "answer": content,
                        "thinking": thinking or "",
                        "tool_calls": tool_calls,
                    }
                )

            return content

    def _build_system_prompt(self) -> str:
        prompt_parts = [self._settings.agent_system_prompt.strip()]
        no_match_instruction = self._settings.no_match_instruction.strip()
        if no_match_instruction:
            prompt_parts.append(f"No-match guidance: {no_match_instruction}")
        return "\n\n".join(part for part in prompt_parts if part)

    def _build_tool(self) -> FunctionTool:
        def _to_lookup_match(hit: RetrievalHit) -> FaqLookupMatch:
            return FaqLookupMatch(faq_id=hit.faq_id, answer=hit.answer, score=hit.score)

        async def faq_lookup(question: str) -> str:
            retrieval_result = await asyncio.to_thread(
                self._retriever.retrieve_best_answer, question
            )
            payload = FaqLookupOutput(
                matches=[_to_lookup_match(hit) for hit in retrieval_result.hits]
            )
            return payload.model_dump_json(ensure_ascii=False)

        return FunctionTool.from_defaults(
            async_fn=faq_lookup,
            name=FAQ_TOOL_NAME,
            description=self._settings.faq_tool_description,
            return_direct=False,
            fn_schema=FaqLookupInput,
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

    async def _collect_event_data(
        self, handler: Any
    ) -> tuple[str | None, list[dict[str, Any]], bool]:
        thinking: str | None = None
        tool_calls: list[dict[str, Any]] = []
        has_tool_error = False
        async for event in handler.stream_events():
            if isinstance(event, AgentOutput):
                event_thinking = self._extract_thinking(event.raw, event.response)
                if event_thinking:
                    thinking = event_thinking
            elif isinstance(event, ToolCallResult):
                has_tool_error = has_tool_error or event.tool_output.is_error
                tool_calls.append(self._serialize_tool_call(event))

        return thinking, tool_calls, has_tool_error

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
