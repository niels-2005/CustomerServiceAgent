"""Redis-backed session-scoped chat memory.

Memory is stored per ``session_id`` and bounded by message count so a single
conversation cannot grow without limit.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from llama_index.core.base.llms.types import ChatMessage
from redis.exceptions import RedisError

_APPEND_TURN_SCRIPT = """
local key = KEYS[1]
local max_messages = tonumber(ARGV[1])
local ttl_seconds = tonumber(ARGV[2])

if redis.call("EXISTS", key) == 1 then
    local current_messages = redis.call("LLEN", key)
    if current_messages + 2 > max_messages then
        return 0
    end
end

redis.call("RPUSH", key, ARGV[3], ARGV[4])
redis.call("EXPIRE", key, ttl_seconds)
return 1
"""


class MemoryBackendError(RuntimeError):
    """Raised when the configured chat history backend cannot be used safely."""


class SessionTurnLimitReachedError(RuntimeError):
    """Raised when a session has already reached its configured message cap."""


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


class SupportsRedisChatHistory(Protocol):
    """Minimal async Redis client surface used by the chat history backend."""

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        """Return stored list items for one Redis key."""

    async def eval(self, script: str, numkeys: int, key: str, *args: str) -> Any:
        """Evaluate the append script atomically."""


class RedisSessionMemoryBackend:
    """Redis-backed short-term chat history with rolling TTL and atomic limits."""

    def __init__(
        self,
        *,
        redis_client: SupportsRedisChatHistory,
        key_prefix: str,
        ttl_seconds: int,
        max_turns: int = 20,
    ) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._max_messages = max_turns

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        """Return the current transcript for one session from Redis."""
        try:
            entries = await self._redis.lrange(self._session_key(session_id), 0, -1)
        except RedisError as exc:
            raise MemoryBackendError("Redis chat history is temporarily unavailable.") from exc

        try:
            return [ChatMessage.model_validate(json.loads(entry)) for entry in entries]
        except Exception as exc:
            raise MemoryBackendError("Redis chat history could not be decoded safely.") from exc

    async def append_turn(
        self,
        session_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        """Atomically append one turn while preserving the hard message cap."""
        try:
            appended = await self._redis.eval(
                _APPEND_TURN_SCRIPT,
                1,
                self._session_key(session_id),
                str(self._max_messages),
                str(self._ttl_seconds),
                self._serialize_message(user_message),
                self._serialize_message(assistant_message),
            )
        except RedisError as exc:
            raise MemoryBackendError("Redis chat history is temporarily unavailable.") from exc

        if appended != 1:
            raise SessionTurnLimitReachedError(
                f"Session '{session_id}' already reached the configured message limit."
            )

    def _session_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:{session_id}"

    @staticmethod
    def _serialize_message(message: ChatMessage) -> str:
        return json.dumps(message.model_dump(mode="json"), separators=(",", ":"))
