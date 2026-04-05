from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from llama_index.core.base.llms.types import ChatMessage

from customer_bot.memory.backend import SessionMemoryBackend


class SupportsAnswer(Protocol):
    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
    ) -> str:
        """Return assistant answer text."""


@dataclass(slots=True)
class ChatResult:
    answer: str
    session_id: str


class ChatService:
    def __init__(self, memory_backend: SessionMemoryBackend, agent_service: SupportsAnswer) -> None:
        self._memory_backend = memory_backend
        self._agent_service = agent_service

    async def chat(self, user_message: str, session_id: str | None = None) -> ChatResult:
        resolved_session_id = session_id or str(uuid4())
        history = await self._memory_backend.get_history(resolved_session_id)

        answer = await self._agent_service.answer(
            user_message=user_message,
            chat_history=history,
            session_id=resolved_session_id,
        )

        await self._memory_backend.append_turn(
            session_id=resolved_session_id,
            user_message=ChatMessage(role="user", content=user_message),
            assistant_message=ChatMessage(role="assistant", content=answer),
        )

        return ChatResult(answer=answer, session_id=resolved_session_id)
