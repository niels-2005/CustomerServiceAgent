from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from customer_bot.api.deps import get_chat_service
from customer_bot.api.main import create_app
from customer_bot.chat.service import ChatResult


class FakeChatService:
    async def chat(self, user_message: str, session_id: str | None = None) -> ChatResult:
        resolved = session_id or "generated-session"
        return ChatResult(answer=f"echo:{user_message}", session_id=resolved)


@pytest.mark.unit
def test_health_endpoint() -> None:
    app = create_app(enable_observability=False)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_chat_endpoint_returns_answer_and_session() -> None:
    app = create_app(enable_observability=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"user_message": "Hallo"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "echo:Hallo",
        "session_id": "generated-session",
    }


@pytest.mark.unit
def test_chat_endpoint_validates_payload() -> None:
    app = create_app(enable_observability=False)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"session_id": "x"})

    assert response.status_code == 422
