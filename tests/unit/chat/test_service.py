"""Unit tests for chat turn orchestration and session memory behavior."""

from __future__ import annotations

import asyncio

import pytest
from llama_index.core.base.llms.types import ChatMessage

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.chat.service import ChatService


class StubMemoryBackend:
    def __init__(self) -> None:
        self._messages: dict[str, list[ChatMessage]] = {}

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self._messages.get(session_id, []))

    async def append_turn(
        self,
        session_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        self._messages.setdefault(session_id, []).extend([user_message, assistant_message])

    async def seed_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        self._messages[session_id] = list(messages)


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


class ErrorAgentService:
    def __init__(self) -> None:
        self.calls = 0

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
        parent_observation: object | None = None,
    ) -> AgentAnswerResult:
        del user_message, chat_history, session_id, parent_observation
        self.calls += 1
        return AgentAnswerResult(answer="Technischer Fehler.", has_execution_error=True)


@pytest.mark.unit
def test_chat_service_reuses_history_for_same_session(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(),
    )

    first = asyncio.run(service.chat("Hallo", session_id="s-1"))
    second = asyncio.run(service.chat("Noch eine Frage", session_id="s-1"))

    assert first.session_id == "s-1"
    assert second.session_id == "s-1"
    assert fake_agent.history_lengths == [0, 2]


@pytest.mark.unit
def test_chat_service_isolates_sessions(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(),
    )

    asyncio.run(service.chat("A", session_id="session-a"))
    asyncio.run(service.chat("B", session_id="session-b"))

    assert fake_agent.history_lengths == [0, 0]


@pytest.mark.unit
def test_chat_service_generates_session_id(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(),
    )

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


class ExplodingInputGuardrailService:
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate_input(self, **kwargs):
        del kwargs
        self.calls += 1
        raise RuntimeError("input exploded")


class RecordingOutputGuardrailService:
    def __init__(self) -> None:
        self.input_calls = 0
        self.output_calls = 0

    async def evaluate_input(self, **kwargs):
        del kwargs
        self.input_calls += 1
        from customer_bot.guardrails.models import GuardrailInputResult

        return GuardrailInputResult(
            action="allow",
            reason=None,
            message=None,
            sanitized_user_message="Hallo",
        )

    async def evaluate_output(self, **kwargs):
        del kwargs
        self.output_calls += 1
        from customer_bot.guardrails.models import GuardrailOutputResult

        return GuardrailOutputResult(
            action="allow",
            reason=None,
            rewrite_hint=None,
            sanitized=False,
        )


class ExplodingOutputGuardrailService(RecordingOutputGuardrailService):
    async def evaluate_output(self, **kwargs):
        del kwargs
        self.output_calls += 1
        raise RuntimeError("output exploded")


@pytest.mark.unit
def test_chat_service_blocks_and_redacts_user_turn(settings_factory) -> None:
    memory = StubMemoryBackend()
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
    memory = StubMemoryBackend()
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
def test_chat_service_falls_back_immediately_when_input_guardrail_errors(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(guardrails_enabled=True),
        guardrail_service=ExplodingInputGuardrailService(),
    )

    result = asyncio.run(service.chat("Meine IBAN ist ...", session_id="s-1"))
    history = asyncio.run(memory.get_history("s-1"))

    assert result.status == "fallback"
    assert result.guardrail_reason is None
    assert result.sanitized is True
    assert fake_agent.history_lengths == []
    assert history[0].content == "[redacted]"
    assert history[1].content == "Technischer Fehler."


@pytest.mark.unit
def test_chat_service_skips_output_guardrails_after_agent_execution_error(
    settings_factory,
) -> None:
    memory = StubMemoryBackend()
    guardrail_service = RecordingOutputGuardrailService()
    agent_service = ErrorAgentService()
    settings = settings_factory(guardrails_enabled=True)
    service = ChatService(
        memory_backend=memory,
        agent_service=agent_service,
        settings=settings,
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Hallo", session_id="s-1"))
    history = asyncio.run(memory.get_history("s-1"))

    assert result.status == "fallback"
    assert result.guardrail_reason is None
    assert agent_service.calls == 1
    assert guardrail_service.output_calls == 0
    assert history[-1].content == settings.messages.error_fallback_text


@pytest.mark.unit
def test_chat_service_returns_current_trace_id_when_langfuse_is_configured(
    monkeypatch, settings_factory
) -> None:
    memory = StubMemoryBackend()
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


class FakeRewriteGuardrailService:
    def __init__(self, *, final_action: str = "allow") -> None:
        self.rewrite_calls = 0
        self.output_calls = 0
        self.final_action = final_action

    async def evaluate_input(self, **kwargs):
        del kwargs
        from customer_bot.guardrails.models import GuardrailInputResult

        return GuardrailInputResult(
            action="allow",
            reason=None,
            message=None,
            sanitized_user_message="Hallo",
        )

    async def evaluate_output(self, **kwargs):
        del kwargs
        from customer_bot.guardrails.models import GuardrailOutputResult

        self.output_calls += 1
        if self.output_calls == 1:
            return GuardrailOutputResult(
                action="rewrite",
                reason="output_sensitive_data",
                rewrite_hint="Remove secrets.",
                sanitized=True,
            )
        return GuardrailOutputResult(
            action=self.final_action,  # type: ignore[arg-type]
            reason="grounding" if self.final_action == "fallback" else None,
            rewrite_hint=None,
            sanitized=False,
        )

    async def rewrite_output(self, **kwargs):
        del kwargs
        from customer_bot.guardrails.models import GuardrailRewriteResult

        self.rewrite_calls += 1
        return GuardrailRewriteResult(answer="rewritten answer", sanitized=False)


class ExplodingRewriteGuardrailService(FakeRewriteGuardrailService):
    async def rewrite_output(self, **kwargs):
        del kwargs
        self.rewrite_calls += 1
        raise RuntimeError("rewrite exploded")


@pytest.mark.unit
def test_chat_service_rewrites_and_rechecks_output_when_retry_budget_exists(
    settings_factory,
) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    guardrail_service = FakeRewriteGuardrailService(final_action="allow")
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings_factory(guardrails_enabled=True, guardrails_max_output_retries=1),
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Hallo", session_id="s-1"))
    history = asyncio.run(memory.get_history("s-1"))

    assert result.answer == "rewritten answer"
    assert result.retry_used is True
    assert result.sanitized is True
    assert guardrail_service.rewrite_calls == 1
    assert guardrail_service.output_calls == 2
    assert history[-1].content == "rewritten answer"


@pytest.mark.unit
def test_chat_service_uses_fallback_when_rewritten_answer_still_fails(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    guardrail_service = FakeRewriteGuardrailService(final_action="fallback")
    settings = settings_factory(guardrails_enabled=True, guardrails_max_output_retries=1)
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings,
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Hallo", session_id="s-1"))

    assert result.status == "fallback"
    assert result.guardrail_reason == "grounding"
    assert result.answer == settings.messages.error_fallback_text


@pytest.mark.unit
def test_chat_service_returns_session_limit_before_agent_execution(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    settings = settings_factory(memory_max_turns=20)
    service = ChatService(memory_backend=memory, agent_service=fake_agent, settings=settings)

    full_history = [
        ChatMessage(role="user", content=f"user-{index}")
        if index % 2 == 0
        else ChatMessage(role="assistant", content=f"assistant-{index}")
        for index in range(20)
    ]
    asyncio.run(memory.seed_history("s-limit", full_history))

    result = asyncio.run(service.chat("Noch eine Frage", session_id="s-limit"))

    assert result.status == "session_limit"
    assert result.answer == settings.memory.session_limit_text
    assert fake_agent.history_lengths == []
    assert len(asyncio.run(memory.get_history("s-limit"))) == 20


@pytest.mark.unit
def test_chat_service_falls_back_when_output_guardrail_errors(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    guardrail_service = ExplodingOutputGuardrailService()
    settings = settings_factory(guardrails_enabled=True)
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings,
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Hallo", session_id="s-1"))

    assert result.status == "fallback"
    assert result.guardrail_reason is None
    assert guardrail_service.output_calls == 1
    assert result.answer == settings.messages.error_fallback_text


@pytest.mark.unit
def test_chat_service_falls_back_when_output_rewrite_errors(settings_factory) -> None:
    memory = StubMemoryBackend()
    fake_agent = FakeAgentService()
    guardrail_service = ExplodingRewriteGuardrailService(final_action="allow")
    settings = settings_factory(guardrails_enabled=True, guardrails_max_output_retries=1)
    service = ChatService(
        memory_backend=memory,
        agent_service=fake_agent,
        settings=settings,
        guardrail_service=guardrail_service,
    )

    result = asyncio.run(service.chat("Hallo", session_id="s-1"))

    assert result.status == "fallback"
    assert result.guardrail_reason is None
    assert result.retry_used is False
    assert guardrail_service.rewrite_calls == 1
    assert result.answer == settings.messages.error_fallback_text


class FailingMemoryBackend:
    async def get_history(self, session_id: str) -> list[ChatMessage]:
        del session_id
        from customer_bot.memory.backend import MemoryBackendError

        raise MemoryBackendError("redis unavailable")

    async def append_turn(
        self,
        session_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        del session_id, user_message, assistant_message


@pytest.mark.unit
def test_chat_service_uses_fallback_when_memory_backend_fails(settings_factory) -> None:
    fake_agent = FakeAgentService()
    settings = settings_factory()
    service = ChatService(
        memory_backend=FailingMemoryBackend(),
        agent_service=fake_agent,
        settings=settings,
    )

    result = asyncio.run(service.chat("Hallo", session_id="s-1"))

    assert result.status == "fallback"
    assert result.answer == settings.messages.error_fallback_text
    assert fake_agent.history_lengths == []
