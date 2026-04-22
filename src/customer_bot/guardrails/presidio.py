from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PresidioDetectionResult:
    sanitized_text: str
    triggered: bool
    reason: str


class PresidioPIIDetector:
    def __init__(self, entities: list[str]) -> None:
        self._analyzer = self._load_analyzer()
        self._entities = self._validate_entities(entities)
        self._anonymizer = self._load_anonymizer()

    def analyze(self, text: str) -> PresidioDetectionResult:
        analyzer_results = self._analyzer.analyze(
            text=text,
            language="en",
            entities=self._entities,
        )

        if not analyzer_results:
            return PresidioDetectionResult(
                sanitized_text=text,
                triggered=False,
                reason="No sensitive data detected.",
            )

        sanitized = self._anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
        )
        return PresidioDetectionResult(
            sanitized_text=sanitized.text,
            triggered=True,
            reason="PII detected by Presidio.",
        )

    def _validate_entities(self, entities: list[str]) -> list[str]:
        supported_entities = set(self._analyzer.registry.get_supported_entities())
        unsupported_entities: list[str] = []
        configured_entities: list[str] = []
        for entity in entities:
            if entity not in supported_entities:
                unsupported_entities.append(entity)
            else:
                configured_entities.append(entity)

        if unsupported_entities:
            supported = ", ".join(sorted(supported_entities))
            unsupported = ", ".join(sorted(unsupported_entities))
            raise RuntimeError(
                "Unsupported Presidio entities configured: "
                f"{unsupported}. Supported by installed Presidio recognizers: {supported}."
            )

        return configured_entities

    @staticmethod
    def _load_analyzer() -> Any:
        module = importlib.import_module("presidio_analyzer")
        analyzer_cls = getattr(module, "AnalyzerEngine", None)
        if analyzer_cls is None:
            raise RuntimeError("presidio_analyzer.AnalyzerEngine is unavailable.")
        return analyzer_cls()

    @staticmethod
    def _load_anonymizer() -> Any:
        module = importlib.import_module("presidio_anonymizer")
        anonymizer_cls = getattr(module, "AnonymizerEngine", None)
        if anonymizer_cls is None:
            raise RuntimeError("presidio_anonymizer.AnonymizerEngine is unavailable.")
        return anonymizer_cls()
