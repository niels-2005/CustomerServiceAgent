from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from llama_index.core.agent.workflow.workflow_events import AgentOutput
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.embeddings import MockEmbedding

from customer_bot.api.deps import get_chat_service
from customer_bot.api.main import create_app
from customer_bot.api.rate_limit import limiter
from customer_bot.chat.service import ChatResult
from tests.unit.agent.fakes import FakeHandler


class StaticFunctionAgent:
    """Provider-free stand-in for the LlamaIndex function agent."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._name = kwargs.get("name", "FAQAgent")

    def run(self, *, user_msg: str, chat_history: list[ChatMessage]) -> FakeHandler:
        del chat_history
        event = AgentOutput(
            response=ChatMessage(role="assistant", content=f"handled:{user_msg}"),
            current_agent_name=self._name,
            raw={"message": {"thinking": "Static integration answer."}},
        )
        return FakeHandler(events=[event], result=event)


class ExplodingChatService:
    async def chat(self, user_message: str, session_id: str | None = None) -> ChatResult:
        del user_message, session_id
        raise RuntimeError("chat exploded")


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    if hasattr(limiter._storage, "reset"):
        limiter._storage.reset()  # type: ignore[attr-defined]


def _configure_runtime(monkeypatch: pytest.MonkeyPatch, settings) -> None:
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.deps.create_llm", lambda settings: object())
    monkeypatch.setattr(
        "customer_bot.retrieval.service.create_embedding_model",
        lambda settings: MockEmbedding(embed_dim=8),
    )
    monkeypatch.setattr("customer_bot.agent.service.FunctionAgent", StaticFunctionAgent)


@pytest.mark.integration
def test_health_endpoint_after_real_app_startup(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    settings = settings_factory(guardrails_enabled=False)
    _configure_runtime(monkeypatch, settings)
    app = create_app(enable_observability=False, run_startup_checks=False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-ID"]
    assert app.state.startup_checks_completed is True


@pytest.mark.integration
def test_chat_endpoint_uses_real_route_and_dependency_wiring(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    settings = settings_factory(guardrails_enabled=False)
    _configure_runtime(monkeypatch, settings)
    app = create_app(enable_observability=False, run_startup_checks=True)

    with TestClient(app) as client:
        response = client.post("/chat", json={"user_message": "Hallo Integration"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "handled:Hallo Integration",
        "session_id": response.json()["session_id"],
        "trace_id": None,
        "status": "answered",
        "guardrail_reason": None,
        "handoff_required": False,
        "retry_used": False,
        "sanitized": False,
    }
    assert response.headers["X-Request-ID"]


@pytest.mark.integration
def test_chat_endpoint_returns_standard_error_envelope_on_unhandled_exception() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: ExplodingChatService()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/chat", json={"user_message": "Hallo"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    assert response.json()["error"]["message"] == "Internal server error."
    assert response.json()["request_id"] != "unknown"


@pytest.mark.integration
def test_rate_limit_is_enforced_in_real_app_stack(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    settings = settings_factory(guardrails_enabled=False)
    _configure_runtime(monkeypatch, settings)
    app = create_app(enable_observability=False, run_startup_checks=True)

    with TestClient(app) as client:
        responses = [
            client.post("/chat", json={"user_message": f"Hallo {index}"}) for index in range(11)
        ]

    assert responses[-1].status_code == 429
    assert responses[-1].json()["error"]["code"] == "rate_limit_exceeded"
    assert responses[-1].json()["request_id"] == responses[-1].headers["X-Request-ID"]
    assert responses[-1].headers["Retry-After"]


@pytest.mark.integration
def test_health_endpoint_is_exempt_from_global_limit_in_real_app(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    settings = settings_factory(guardrails_enabled=False)
    _configure_runtime(monkeypatch, settings)
    app = create_app(enable_observability=False, run_startup_checks=True)

    with TestClient(app) as client:
        responses = [client.get("/health") for _ in range(65)]

    assert all(response.status_code == 200 for response in responses)


@pytest.mark.integration
def test_startup_checks_fail_when_chat_stack_cannot_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory,
) -> None:
    settings = settings_factory(guardrails_enabled=False)
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)

    def fail_llm(settings):
        del settings
        raise RuntimeError("llm bootstrap failed")

    monkeypatch.setattr("customer_bot.api.deps.create_llm", fail_llm)
    app = create_app(enable_observability=False, run_startup_checks=True)

    with pytest.raises(RuntimeError, match="llm bootstrap failed"):
        with TestClient(app):
            pass
