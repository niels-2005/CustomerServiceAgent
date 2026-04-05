from __future__ import annotations

import asyncio

import pytest
from llama_index.core.base.llms.types import ChatMessage

from customer_bot.chat.service import ChatService
from customer_bot.memory.backend import InMemorySessionMemoryBackend


class FakeAgentService:
    def __init__(self) -> None:
        self.history_lengths: list[int] = []

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
    ) -> str:
        self.history_lengths.append(len(chat_history))
        return f"answer:{user_message}:{session_id}"


@pytest.mark.unit
def test_chat_service_reuses_history_for_same_session() -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    service = ChatService(memory_backend=memory, agent_service=fake_agent)

    first = asyncio.run(service.chat("Hallo", session_id="s-1"))
    second = asyncio.run(service.chat("Noch eine Frage", session_id="s-1"))

    assert first.session_id == "s-1"
    assert second.session_id == "s-1"
    assert fake_agent.history_lengths == [0, 2]


@pytest.mark.unit
def test_chat_service_isolates_sessions() -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    service = ChatService(memory_backend=memory, agent_service=fake_agent)

    asyncio.run(service.chat("A", session_id="session-a"))
    asyncio.run(service.chat("B", session_id="session-b"))

    assert fake_agent.history_lengths == [0, 0]


@pytest.mark.unit
def test_chat_service_generates_session_id() -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    service = ChatService(memory_backend=memory, agent_service=fake_agent)

    result = asyncio.run(service.chat("Hallo"))

    assert result.session_id
    assert result.answer.startswith("answer:Hallo")
