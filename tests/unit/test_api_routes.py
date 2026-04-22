from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from customer_bot.api.deps import get_chat_service
from customer_bot.api.main import create_app
from customer_bot.api.rate_limit import limiter
from customer_bot.chat.service import ChatResult


class FakeChatService:
    async def chat(self, user_message: str, session_id: str | None = None) -> ChatResult:
        resolved = session_id or "generated-session"
        return ChatResult(
            answer=f"echo:{user_message}",
            session_id=resolved,
            status="answered",
            guardrail_reason=None,
            handoff_required=False,
            retry_used=False,
            sanitized=False,
        )


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    limiter._storage.reset()  # type: ignore[attr-defined]


@pytest.mark.unit
def test_health_endpoint() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-ID"]


@pytest.mark.unit
def test_chat_endpoint_returns_answer_and_session() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"user_message": "Hallo"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "echo:Hallo",
        "session_id": "generated-session",
        "status": "answered",
        "guardrail_reason": None,
        "handoff_required": False,
        "retry_used": False,
        "sanitized": False,
    }
    assert response.headers["X-Request-ID"]


@pytest.mark.unit
def test_chat_endpoint_validates_payload() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"session_id": "x"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_request"
    assert body["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.unit
def test_chat_endpoint_returns_passed_request_id() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"user_message": "Hallo"},
        headers={"X-Request-ID": "req-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


@pytest.mark.unit
def test_chat_endpoint_rejects_too_long_user_message() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"user_message": "x" * 501})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.unit
def test_chat_endpoint_rejects_blank_user_message() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"user_message": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.unit
def test_chat_endpoint_uses_configured_user_message_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    class _Settings:
        api_max_user_message_length = 5

    monkeypatch.setattr("customer_bot.api.models.get_settings", lambda: _Settings())
    response = client.post("/chat", json={"user_message": "123456"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.unit
def test_chat_endpoint_trims_user_message_and_session_id() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"user_message": "  Hallo  ", "session_id": "  session-1  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "echo:Hallo",
        "session_id": "session-1",
        "status": "answered",
        "guardrail_reason": None,
        "handoff_required": False,
        "retry_used": False,
        "sanitized": False,
    }


@pytest.mark.unit
def test_blank_session_id_is_treated_as_missing() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"user_message": "Hallo", "session_id": "   "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "echo:Hallo",
        "session_id": "generated-session",
        "status": "answered",
        "guardrail_reason": None,
        "handoff_required": False,
        "retry_used": False,
        "sanitized": False,
    }


@pytest.mark.unit
def test_cors_preflight_allows_configured_origin() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    client = TestClient(app)

    response = client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


@pytest.mark.unit
def test_trusted_host_rejects_unknown_host() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    client = TestClient(app)

    response = client.get("/health", headers={"host": "evil.example"})

    assert response.status_code == 400
    assert response.text == "Invalid host header"
    assert response.headers["X-Request-ID"]


@pytest.mark.unit
def test_chat_endpoint_enforces_rate_limit() -> None:
    app = create_app(enable_observability=False, run_startup_checks=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    responses = [client.post("/chat", json={"user_message": f"Hallo {idx}"}) for idx in range(11)]

    assert responses[-1].status_code == 429
    assert responses[-1].json()["error"]["code"] == "rate_limit_exceeded"
    assert responses[-1].json()["request_id"] == responses[-1].headers["X-Request-ID"]


@pytest.mark.unit
def test_startup_checks_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_chat_service():
        raise RuntimeError("startup failed")

    monkeypatch.setattr("customer_bot.api.main.get_chat_service", fail_chat_service)
    app = create_app(enable_observability=False, run_startup_checks=True)

    with pytest.raises(RuntimeError, match="startup failed"):
        with TestClient(app):
            pass
