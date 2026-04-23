from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from customer_bot.guardrails.presidio import (
    PresidioDetectionResult,
    PresidioPIIDetector,
    _load_presidio_runtime,
)
from customer_bot.guardrails.validators.secret_pii import OutputSensitiveDataGuard, SecretPIIGuard


class _FakeDetector:
    def __init__(
        self,
        *,
        entities: list[str],
        config_path,
        language: str,
        allow_list: list[str] | None = None,
        score_threshold: float | None = None,
    ) -> None:
        self.entities = entities
        self.config_path = config_path
        self.language = language
        self.allow_list = allow_list or []
        self.score_threshold = score_threshold

    def analyze(self, text: str) -> PresidioDetectionResult:
        return PresidioDetectionResult(
            sanitized_text=text.replace("max@example.com", "<EMAIL_ADDRESS>"),
            triggered="@" in text,
            reason=(
                "PII detected by Presidio: EMAIL_ADDRESS."
                if "@" in text
                else "No sensitive data detected."
            ),
        )


class _FakeAnalyzer:
    def __init__(self, results, supported_entities: list[str]) -> None:
        self._results = results
        self._supported_entities = supported_entities
        self.calls: list[dict[str, object]] = []

    def get_supported_entities(self, language: str) -> list[str]:
        assert language == "de"
        return self._supported_entities

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        return self._results


class _FakeAnonymizer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def anonymize(self, *, text: str, analyzer_results, operators):
        self.calls.append(
            {"text": text, "analyzer_results": analyzer_results, "operators": operators}
        )
        sanitized = text
        for result in analyzer_results:
            placeholder = operators[result.entity_type].params["new_value"]
            sanitized = sanitized[: result.start] + placeholder + sanitized[result.end :]
        return SimpleNamespace(text=sanitized)


def _recognizer_result(entity_type: str, start: int, end: int, score: float = 0.8):
    return SimpleNamespace(entity_type=entity_type, start=start, end=end, score=score)


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
    assert sanitized == "Kontakt: <EMAIL_ADDRESS>"
    assert check.reason == "PII detected by Presidio: EMAIL_ADDRESS."


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
def test_presidio_detector_uses_language_allow_list_threshold_and_placeholders(
    monkeypatch, settings_factory
) -> None:
    _load_presidio_runtime.cache_clear()
    analyzer = _FakeAnalyzer(
        results=[_recognizer_result("LOCATION", 8, 14)],
        supported_entities=["EMAIL_ADDRESS", "LOCATION"],
    )
    anonymizer = _FakeAnonymizer()
    monkeypatch.setattr(
        "customer_bot.guardrails.presidio._load_presidio_runtime",
        lambda _config_path: SimpleNamespace(analyzer=analyzer, anonymizer=anonymizer),
    )
    settings = settings_factory(
        guardrails_presidio_language="de",
        guardrails_presidio_allow_list=["Berlin"],
        guardrails_presidio_score_threshold=0.55,
    )

    detector = PresidioPIIDetector(
        entities=["LOCATION"],
        config_path=settings.guardrails_presidio_config_path,
        language=settings.guardrails_presidio_language,
        allow_list=settings.guardrails_presidio_allow_list,
        score_threshold=settings.guardrails_presidio_score_threshold,
    )
    result = detector.analyze("Adresse Berlin")

    assert result.triggered is True
    assert result.sanitized_text == "Adresse <LOCATION>"
    assert result.reason == "PII detected by Presidio: LOCATION."
    assert analyzer.calls == [
        {
            "text": "Adresse Berlin",
            "language": "de",
            "entities": ["LOCATION"],
            "allow_list": ["Berlin"],
            "score_threshold": 0.55,
        }
    ]
    assert anonymizer.calls[0]["operators"]["LOCATION"].params["new_value"] == "<LOCATION>"


@pytest.mark.unit
def test_presidio_detector_errors_for_unknown_entity_in_language(
    monkeypatch, settings_factory
) -> None:
    _load_presidio_runtime.cache_clear()
    analyzer = _FakeAnalyzer(results=[], supported_entities=["EMAIL_ADDRESS", "LOCATION"])
    monkeypatch.setattr(
        "customer_bot.guardrails.presidio._load_presidio_runtime",
        lambda _config_path: SimpleNamespace(analyzer=analyzer, anonymizer=_FakeAnonymizer()),
    )
    settings = settings_factory()

    detector = PresidioPIIDetector(
        entities=["TOTALLY_UNKNOWN_ENTITY"],
        config_path=settings.guardrails_presidio_config_path,
        language=settings.guardrails_presidio_language,
        allow_list=settings.guardrails_presidio_allow_list,
        score_threshold=settings.guardrails_presidio_score_threshold,
    )

    with pytest.raises(
        RuntimeError, match="Unsupported Presidio entities configured for language 'de'"
    ):
        detector.analyze("Unkritischer Text")


@pytest.mark.unit
def test_presidio_detector_errors_for_missing_config_file(settings_factory) -> None:
    detector = PresidioPIIDetector(
        entities=["LOCATION"],
        config_path="missing-presidio-config.yaml",
        language="de",
        allow_list=[],
        score_threshold=0.4,
    )

    with pytest.raises(RuntimeError, match="Presidio config file does not exist"):
        detector.analyze("Berlin")
