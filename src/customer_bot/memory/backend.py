"""Session-scoped chat memory backends.

Memory is stored per ``session_id`` and bounded by turn count so a single
conversation cannot grow without limit.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Sequence
from typing import Protocol

from llama_index.core.base.llms.types import ChatMessage


class SessionMemoryBackend(Protocol):
    """Interface for chat history stores keyed by session ID."""

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
    """In-process session memory backend for local runtime and tests.

    Each turn stores one user message plus one assistant message, so the
    configured turn limit is tracked internally as ``max_turns * 2`` messages.
    """

    def __init__(self, max_turns: int = 10) -> None:
        self._max_messages = max_turns * 2
        self._sessions: dict[str, deque[ChatMessage]] = {}
        self._lock = asyncio.Lock()

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        """Return the current transcript for one session."""
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
        """Append one user/assistant turn to the bounded session transcript."""
        async with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                history = deque(maxlen=self._max_messages)
                self._sessions[session_id] = history
            history.extend([user_message, assistant_message])

    async def seed_history(self, session_id: str, messages: Sequence[ChatMessage]) -> None:
        """Replace a session transcript with the most recent bounded history."""
        async with self._lock:
            self._sessions[session_id] = deque(
                messages[-self._max_messages :],
                maxlen=self._max_messages,
            )
