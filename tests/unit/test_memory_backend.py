from __future__ import annotations

import asyncio

import pytest
from llama_index.core.base.llms.types import ChatMessage

from customer_bot.memory.backend import InMemorySessionMemoryBackend


@pytest.mark.unit
def test_memory_backend_isolates_sessions() -> None:
    backend = InMemorySessionMemoryBackend(max_turns=10)

    asyncio.run(
        backend.append_turn(
            "session-a",
            ChatMessage(role="user", content="u1"),
            ChatMessage(role="assistant", content="a1"),
        )
    )

    history_a = asyncio.run(backend.get_history("session-a"))
    history_b = asyncio.run(backend.get_history("session-b"))

    assert len(history_a) == 2
    assert history_b == []


@pytest.mark.unit
def test_memory_backend_limits_turn_window() -> None:
    backend = InMemorySessionMemoryBackend(max_turns=2)

    for idx in range(3):
        asyncio.run(
            backend.append_turn(
                "session-a",
                ChatMessage(role="user", content=f"u{idx}"),
                ChatMessage(role="assistant", content=f"a{idx}"),
            )
        )

    history = asyncio.run(backend.get_history("session-a"))

    assert len(history) == 4
    assert history[0].content == "u1"
    assert history[-1].content == "a2"
