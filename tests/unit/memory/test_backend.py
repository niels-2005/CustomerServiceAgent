from __future__ import annotations

import asyncio
import json

import pytest
from llama_index.core.base.llms.types import ChatMessage

from customer_bot.memory.backend import (
    MemoryBackendError,
    RedisSessionMemoryBackend,
    SessionTurnLimitReachedError,
)


class FakeRedis:
    def __init__(self) -> None:
        self._data: dict[str, list[str]] = {}
        self.ttls: dict[str, int] = {}

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self._data.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]

    async def eval(self, script: str, numkeys: int, key: str, *args: str) -> int:
        del script, numkeys
        max_messages = int(args[0])
        ttl_seconds = int(args[1])
        values = self._data.setdefault(key, [])
        if len(values) + 2 > max_messages:
            return 0
        values.extend([args[2], args[3]])
        self.ttls[key] = ttl_seconds
        return 1


@pytest.mark.unit
def test_redis_memory_backend_preserves_order_and_refreshes_ttl() -> None:
    redis_client = FakeRedis()
    backend = RedisSessionMemoryBackend(
        redis_client=redis_client,
        key_prefix="customer-bot:test:memory",
        ttl_seconds=86400,
        max_turns=20,
    )

    asyncio.run(
        backend.append_turn(
            "session-a",
            ChatMessage(role="user", content="u1"),
            ChatMessage(role="assistant", content="a1"),
        )
    )
    asyncio.run(
        backend.append_turn(
            "session-a",
            ChatMessage(role="user", content="u2"),
            ChatMessage(role="assistant", content="a2"),
        )
    )

    history = asyncio.run(backend.get_history("session-a"))

    assert [message.content for message in history] == ["u1", "a1", "u2", "a2"]
    assert redis_client.ttls["customer-bot:test:memory:session-a"] == 86400
    serialized = redis_client._data["customer-bot:test:memory:session-a"][0]
    assert json.loads(serialized)["role"] == "user"


@pytest.mark.unit
def test_redis_memory_backend_rejects_append_when_session_is_full() -> None:
    redis_client = FakeRedis()
    backend = RedisSessionMemoryBackend(
        redis_client=redis_client,
        key_prefix="customer-bot:test:memory",
        ttl_seconds=86400,
        max_turns=4,
    )

    for idx in range(2):
        asyncio.run(
            backend.append_turn(
                "session-a",
                ChatMessage(role="user", content=f"u{idx}"),
                ChatMessage(role="assistant", content=f"a{idx}"),
            )
        )

    with pytest.raises(SessionTurnLimitReachedError):
        asyncio.run(
            backend.append_turn(
                "session-a",
                ChatMessage(role="user", content="u2"),
                ChatMessage(role="assistant", content="a2"),
            )
        )


@pytest.mark.unit
def test_redis_memory_backend_raises_on_invalid_serialized_message() -> None:
    redis_client = FakeRedis()
    redis_client._data["customer-bot:test:memory:session-a"] = ["{not-json}"]
    backend = RedisSessionMemoryBackend(
        redis_client=redis_client,
        key_prefix="customer-bot:test:memory",
        ttl_seconds=86400,
        max_turns=20,
    )

    with pytest.raises(MemoryBackendError, match="could not be decoded safely"):
        asyncio.run(backend.get_history("session-a"))
