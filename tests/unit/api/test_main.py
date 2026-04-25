from __future__ import annotations

from fastapi.testclient import TestClient

from customer_bot.api.main import create_app


def test_lifespan_sets_runtime_state_and_flushes_langfuse_client(
    monkeypatch, settings_factory
) -> None:
    settings = settings_factory()
    flushed: list[str] = []

    class FakeLangfuseClient:
        def flush(self) -> None:
            flushed.append("flush")

    monkeypatch.setattr("customer_bot.api.main.get_runtime_settings", lambda: settings)
    monkeypatch.setattr("customer_bot.api.main.get_chat_service", lambda: object())
    monkeypatch.setattr(
        "customer_bot.api.main.initialize_observability",
        lambda _settings: FakeLangfuseClient(),
    )

    app = create_app(enable_observability=True, run_startup_checks=True)

    with TestClient(app):
        assert app.state.runtime_settings is settings
        assert app.state.startup_checks_completed is True
        assert app.state.langfuse_client is not None

    assert flushed == ["flush"]


def test_lifespan_skips_startup_chat_stack_when_disabled(monkeypatch, settings_factory) -> None:
    settings = settings_factory()
    startup_calls: list[str] = []

    monkeypatch.setattr("customer_bot.api.main.get_runtime_settings", lambda: settings)
    monkeypatch.setattr(
        "customer_bot.api.main.get_chat_service",
        lambda: startup_calls.append("chat_service"),
    )

    app = create_app(enable_observability=False, run_startup_checks=False)

    with TestClient(app):
        assert app.state.langfuse_client is None
        assert app.state.startup_checks_completed is True

    assert startup_calls == []
