from __future__ import annotations

import pytest

import customer_bot.observability as observability_module
from customer_bot.observability import initialize_observability


@pytest.mark.unit
def test_observability_fails_fast_without_keys(settings_factory) -> None:
    settings = settings_factory(
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
        langfuse_fail_fast=True,
    )

    with pytest.raises(RuntimeError, match="Langfuse keys are missing"):
        initialize_observability(settings)


@pytest.mark.unit
def test_observability_non_fatal_without_keys(settings_factory) -> None:
    settings = settings_factory(
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
        langfuse_fail_fast=False,
    )

    client = initialize_observability(settings)

    assert client is None


@pytest.mark.unit
def test_observability_passes_environment_and_release(monkeypatch, settings_factory) -> None:
    settings = settings_factory(
        langfuse_tracing_environment="production",
        langfuse_release="2026.04.17",
    )
    captured: dict[str, object] = {}

    class FakeInstrumentor:
        def instrument(self) -> None:
            return None

    class FakeLangfuse:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def auth_check(self) -> bool:
            return True

    monkeypatch.setattr(observability_module, "_INSTRUMENTED", False)
    monkeypatch.setattr(observability_module, "LlamaIndexInstrumentor", FakeInstrumentor)
    monkeypatch.setattr(observability_module, "Langfuse", FakeLangfuse)

    client = initialize_observability(settings)

    assert client is not None
    assert captured["environment"] == "production"
    assert captured["release"] == "2026.04.17"
    assert callable(captured["mask"])
