from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Sequence
from typing import Protocol

from llama_index.core.base.llms.types import ChatMessage


class SessionMemoryBackend(Protocol):
    async def get_history(self, session_id: str) -> list[ChatMessage]:
        """Return chat history for a session."""

    async def append_turn(
        self,
        session_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        """Append one user/assistant turn for a session."""


class InMemorySessionMemoryBackend:
    def __init__(self, max_turns: int = 10) -> None:
        self._max_messages = max_turns * 2
        self._sessions: dict[str, deque[ChatMessage]] = {}
        self._lock = asyncio.Lock()

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        async with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                return []
            return list(history)

    async def append_turn(
        self,
        session_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        async with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                history = deque(maxlen=self._max_messages)
                self._sessions[session_id] = history
            history.extend([user_message, assistant_message])

    async def seed_history(self, session_id: str, messages: Sequence[ChatMessage]) -> None:
        async with self._lock:
            self._sessions[session_id] = deque(
                messages[-self._max_messages :],
                maxlen=self._max_messages,
            )
