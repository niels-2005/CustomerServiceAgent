"""Unit tests for chat turn orchestration and session memory behavior."""

from __future__ import annotations

import asyncio

import pytest
from llama_index.core.base.llms.types import ChatMessage

from customer_bot.agent.service import AgentAnswerResult
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
        parent_observation: object | None = None,
    ) -> AgentAnswerResult:
        del parent_observation
        self.history_lengths.append(len(chat_history))
        return AgentAnswerResult(answer=f"answer:{user_message}:{session_id}")


@pytest.mark.unit
def test_chat_service_reuses_history_for_same_session() -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    from customer_bot.config import Settings

    service = ChatService(memory_backend=memory, agent_service=fake_agent, settings=Settings())

    first = asyncio.run(service.chat("Hallo", session_id="s-1"))
    second = asyncio.run(service.chat("Noch eine Frage", session_id="s-1"))

    assert first.session_id == "s-1"
    assert second.session_id == "s-1"
    assert fake_agent.history_lengths == [0, 2]


@pytest.mark.unit
def test_chat_service_isolates_sessions() -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    from customer_bot.config import Settings

    service = ChatService(memory_backend=memory, agent_service=fake_agent, settings=Settings())

    asyncio.run(service.chat("A", session_id="session-a"))
    asyncio.run(service.chat("B", session_id="session-b"))

    assert fake_agent.history_lengths == [0, 0]


@pytest.mark.unit
def test_chat_service_generates_session_id() -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    from customer_bot.config import Settings

    service = ChatService(memory_backend=memory, agent_service=fake_agent, settings=Settings())

    result = asyncio.run(service.chat("Hallo"))

    assert result.session_id
    assert result.answer.startswith("answer:Hallo")
    assert result.trace_id is None


class FakeBlockedGuardrailService:
    async def evaluate_input(self, **kwargs):
        del kwargs
        from customer_bot.guardrails.models import GuardrailInputResult

        return GuardrailInputResult(
            action="blocked",
            reason="secret_pii",
            message="blocked",
            sanitized_user_message="[redacted]",
            sanitized=True,
        )


class FakeHandoffGuardrailService:
    async def evaluate_input(self, **kwargs):
        del kwargs
        from customer_bot.guardrails.models import GuardrailInputResult

        return GuardrailInputResult(
            action="handoff",
            reason="escalation",
            message="handoff",
            sanitized_user_message="Was sind die Sportnews heute?",
            sanitized=False,
        )


@pytest.mark.unit
def test_chat_service_blocks_and_redacts_user_turn(settings_factory) -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(
            guardrails_enabled=True,
            LANGFUSE_PUBLIC_KEY="",
            LANGFUSE_SECRET_KEY="",
        ),
        guardrail_service=FakeBlockedGuardrailService(),
    )

    result = asyncio.run(service.chat("Meine IBAN ist ...", session_id="s-1"))
    history = asyncio.run(memory.get_history("s-1"))

    assert result.status == "blocked"
    assert result.guardrail_reason == "secret_pii"
    # Blocked turns must not leak the original sensitive content into memory.
    assert history[0].content == "[redacted]"
    assert history[1].content == "blocked"


@pytest.mark.unit
def test_chat_service_keeps_non_sensitive_handoff_turn_in_history(settings_factory) -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(
            guardrails_enabled=True,
            LANGFUSE_PUBLIC_KEY="",
            LANGFUSE_SECRET_KEY="",
        ),
        guardrail_service=FakeHandoffGuardrailService(),
    )

    result = asyncio.run(service.chat("Was sind die Sportnews heute?", session_id="s-1"))
    history = asyncio.run(memory.get_history("s-1"))

    assert result.status == "handoff"
    assert result.guardrail_reason == "escalation"
    assert history[0].content == "Was sind die Sportnews heute?"
    assert history[1].content == "handoff"


@pytest.mark.unit
def test_chat_service_returns_current_trace_id_when_langfuse_is_configured(
    monkeypatch, settings_factory
) -> None:
    memory = InMemorySessionMemoryBackend(max_turns=10)
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(),
    )
    trace_calls: list[str] = []

    class FakeTraceHelper:
        def propagate_trace_attributes(self, session_id: str):
            trace_calls.append(f"propagate:{session_id}")

            class _Context:
                def __enter__(self):
                    return None

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            return _Context()

        def start_root_observation(self, *, user_message: str, session_id: str):
            trace_calls.append(f"root:{user_message}:{session_id}")

            class _Context:
                def __enter__(self):
                    return object()

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            return _Context()

        def get_current_trace_id(self) -> str | None:
            trace_calls.append("trace-id")
            return "trace-abc"

        def update_root(self, *args, **kwargs) -> None:
            trace_calls.append("update")

    monkeypatch.setattr(service, "_trace_helper", FakeTraceHelper())

    result = asyncio.run(service.chat("Hallo", session_id="session-1"))

    assert result.trace_id == "trace-abc"
    assert trace_calls == [
        "propagate:session-1",
        "root:Hallo:session-1",
        "trace-id",
        "update",
    ]
