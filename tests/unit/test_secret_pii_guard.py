from __future__ import annotations

import asyncio

import pytest

from customer_bot.guardrails.presidio import PresidioDetectionResult, PresidioPIIDetector
from customer_bot.guardrails.validators.secret_pii import OutputSensitiveDataGuard, SecretPIIGuard


class _FakeDetector:
    def __init__(self, entities: list[str]) -> None:
        self.entities = entities

    def analyze(self, text: str) -> PresidioDetectionResult:
        return PresidioDetectionResult(
            sanitized_text=text.replace("max@example.com", "[redacted]"),
            triggered="@" in text,
            reason="PII detected by Presidio." if "@" in text else "No sensitive data detected.",
        )


@pytest.mark.unit
def test_secret_pii_guard_blocks_custom_secret_patterns(settings_factory) -> None:
    guard = SecretPIIGuard(settings_factory())

    blocked, sanitized, check = asyncio.run(guard.check("mein token ist sk-1234567890abcdef"))

    assert blocked is True
    assert "[redacted]" in sanitized
    assert check.name == "secret_pii"
    assert check.decision == "block"


@pytest.mark.unit
def test_secret_pii_guard_uses_presidio_detector(monkeypatch, settings_factory) -> None:
    monkeypatch.setattr(
        "customer_bot.guardrails.validators.secret_pii.PresidioPIIDetector",
        _FakeDetector,
    )
    guard = SecretPIIGuard(settings_factory())

    blocked, sanitized, check = asyncio.run(guard.check("Kontakt: max@example.com"))

    assert blocked is True
    assert sanitized == "Kontakt: [redacted]"
    assert check.reason == "PII detected by Presidio."


@pytest.mark.unit
def test_output_sensitive_data_guard_allows_normal_text(monkeypatch, settings_factory) -> None:
    monkeypatch.setattr(
        "customer_bot.guardrails.validators.secret_pii.PresidioPIIDetector",
        _FakeDetector,
    )
    guard = OutputSensitiveDataGuard(settings_factory())

    blocked, sanitized, check = asyncio.run(guard.check("Alles gut."))

    assert blocked is False
    assert sanitized == "Alles gut."
    assert check.name == "output_sensitive_data"
    assert check.decision == "allow"


@pytest.mark.unit
def test_presidio_detector_supports_ip_address_entity() -> None:
    result = PresidioPIIDetector(["IP_ADDRESS"]).analyze("Server-IP: 192.168.0.1")

    assert result.triggered is True
    assert "<IP_ADDRESS>" in result.sanitized_text
    assert result.reason == "PII detected by Presidio."


@pytest.mark.unit
def test_presidio_detector_errors_for_unknown_entity() -> None:
    with pytest.raises(RuntimeError, match="Supported by installed Presidio recognizers"):
        PresidioPIIDetector(["TOTALLY_UNKNOWN_ENTITY"])
