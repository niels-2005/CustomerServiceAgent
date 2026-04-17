from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from langfuse import get_client, propagate_attributes
from llama_index.core.agent.workflow.workflow_events import AgentOutput, ToolCallResult
from llama_index.core.base.llms.types import ChatMessage, ThinkingBlock

from customer_bot.agent.tooling import FAQ_TOOL_NAME
from customer_bot.config import Settings

LANGFUSE_TRACE_NAME = "chat_request"
LANGFUSE_TRACE_TAGS = ("chat", "faq-agent")
LANGFUSE_SYSTEM_PROMPT_VERSION = "v1"


@dataclass(slots=True)
class CollectedEventData:
    thinking: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    has_tool_error: bool = False
    has_no_match: bool = False

    def __post_init__(self) -> None:
        if self.tool_calls is None:
            self.tool_calls = []


class AgentTraceHelper:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def start_trace_observation(self, user_message: str, session_id: str):
        if not self.is_langfuse_configured():
            return nullcontext(None)

        langfuse = get_client()
        return langfuse.start_as_current_observation(
            name=LANGFUSE_TRACE_NAME,
            as_type="agent",
            input={
                "system_prompt_version": LANGFUSE_SYSTEM_PROMPT_VERSION,
                "user_message": user_message,
                "session_id": session_id,
            },
        )

    def propagate_trace_attributes(self, session_id: str):
        if not self.is_langfuse_configured():
            return nullcontext()
        return propagate_attributes(
            session_id=session_id,
            trace_name=LANGFUSE_TRACE_NAME,
            tags=list(LANGFUSE_TRACE_TAGS),
        )

    def is_langfuse_configured(self) -> bool:
        return bool(self._settings.langfuse_public_key and self._settings.langfuse_secret_key)

    async def collect_event_data(self, handler: Any, root: Any | None = None) -> CollectedEventData:
        thinking_fragments: list[str] = []
        last_thinking_fragment: str | None = None
        collected = CollectedEventData()

        async for event in handler.stream_events():
            if isinstance(event, AgentOutput):
                event_thinking = self._extract_thinking(event.raw, event.response)
                if event_thinking and event_thinking != last_thinking_fragment:
                    thinking_fragments.append(event_thinking)
                last_thinking_fragment = event_thinking
                continue

            if not isinstance(event, ToolCallResult):
                continue

            last_thinking_fragment = None
            tool_call = self._serialize_tool_call(event)
            collected.has_tool_error = collected.has_tool_error or event.tool_output.is_error
            collected.has_no_match = collected.has_no_match or self._is_no_match_tool_call(
                tool_call
            )
            collected.tool_calls.append(self._summarize_tool_call(tool_call))
            if root is not None:
                self.record_tool_observation(root, event, tool_call)

        collected.thinking = "\n\n".join(thinking_fragments)
        return collected

    def update_root_observation(
        self, root: Any, answer: str, collected: CollectedEventData
    ) -> None:
        level, status_message = self.resolve_root_status(
            has_tool_error=collected.has_tool_error,
            has_no_match=collected.has_no_match,
        )
        root.update(
            output={
                "answer": answer,
                "thinking": collected.thinking,
                "tool_calls": collected.tool_calls,
            },
            level=level,
            status_message=status_message,
        )

    def record_tool_observation(
        self,
        root: Any,
        event: ToolCallResult,
        tool_call: dict[str, Any],
    ) -> None:
        level = "ERROR" if tool_call["is_error"] else None
        status_message = f"Tool {event.tool_name} failed" if tool_call["is_error"] else None
        metadata = {"toolid": event.tool_id} if event.tool_id else None
        tool_observation = root.start_observation(
            name=event.tool_name,
            as_type="tool",
            input=tool_call["tool_input"],
            metadata=metadata,
            level=level,
            status_message=status_message,
        )
        tool_observation.update(output=tool_call["tool_output"])
        tool_observation.end()

    @staticmethod
    def resolve_root_status(
        *, has_tool_error: bool, has_no_match: bool
    ) -> tuple[str | None, str | None]:
        if has_tool_error:
            return "ERROR", "Tool or agent execution failed; technical fallback returned."
        if has_no_match:
            return "WARNING", "No FAQ match found."
        return None, None

    def summarize_tool_input(self, value: Any) -> Any:
        if isinstance(value, dict):
            if len(value) == 1:
                only_value = next(iter(value.values()))
                if isinstance(only_value, str):
                    return self._truncate(only_value)
            return value
        if isinstance(value, str):
            return self._truncate(value)
        return value

    def _serialize_tool_call(self, event: ToolCallResult) -> dict[str, Any]:
        return {
            "tool_name": event.tool_name,
            "tool_input": self._json_friendly(event.tool_kwargs),
            "tool_output": self._normalize_tool_output(event),
            "is_error": event.tool_output.is_error,
        }

    def _summarize_tool_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool_name": tool_call["tool_name"],
            "tool_input": self.summarize_tool_input(tool_call["tool_input"]),
            "tool_output": self._render_root_tool_output(
                tool_name=tool_call["tool_name"],
                value=tool_call["tool_output"],
                is_error=tool_call["is_error"],
            ),
            "is_error": tool_call["is_error"],
        }

    def _is_no_match_tool_call(self, tool_call: dict[str, Any]) -> bool:
        if tool_call["tool_name"] != FAQ_TOOL_NAME or tool_call["is_error"]:
            return False

        tool_output = tool_call["tool_output"]
        return isinstance(tool_output, dict) and tool_output.get("matches") == []

    def _normalize_tool_output(self, event: ToolCallResult) -> Any:
        content = event.tool_output.content
        if isinstance(content, str) and content.strip():
            parsed_content = self._parse_json_string(content)
            return self._json_friendly(parsed_content if parsed_content is not None else content)
        if content:
            return self._json_friendly(content)

        raw_output = event.tool_output.raw_output
        if raw_output is None:
            return None

        return self._json_friendly(raw_output)

    def _render_root_tool_output(self, tool_name: str, value: Any, is_error: bool) -> str:
        if tool_name == FAQ_TOOL_NAME:
            faq_output = self._render_faq_root_tool_output(value)
            if faq_output is not None:
                return faq_output

        if isinstance(value, str):
            return self._truncate(value)

        if isinstance(value, dict):
            if is_error:
                error_text = self._extract_error_text(value)
                if error_text is not None:
                    return self._truncate(error_text)
            return self._truncate(self._compact_json(value))

        if isinstance(value, list):
            return self._truncate(self._compact_json(value))

        if value is None:
            return ""

        return self._truncate(str(value))

    def _render_faq_root_tool_output(self, value: Any) -> str | None:
        if isinstance(value, str):
            return self._truncate(value)

        if not isinstance(value, dict):
            return None

        matches = value.get("matches")
        if not isinstance(matches, list):
            return None

        if not matches:
            return "Keine FAQ-Treffer"

        top_match = matches[0]
        if not isinstance(top_match, dict):
            return self._truncate(self._compact_json(top_match))

        answer = top_match.get("answer")
        faq_id = top_match.get("faq_id")
        if isinstance(answer, str) and answer.strip():
            if isinstance(faq_id, str) and faq_id.strip():
                return self._truncate(f"{faq_id}: {answer}")
            return self._truncate(answer)

        return self._truncate(self._compact_json(top_match))

    @staticmethod
    def _extract_error_text(value: dict[str, Any]) -> str | None:
        for key in ("detail", "message", "error"):
            error_value = value.get(key)
            if isinstance(error_value, str) and error_value.strip():
                return error_value
        return None

    @staticmethod
    def _compact_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

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

    @staticmethod
    def _parse_json_string(value: str) -> Any | None:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _truncate(value: str, limit: int = 160) -> str:
        if len(value) <= limit:
            return value
        return f"{value[: limit - 3]}..."
