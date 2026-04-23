from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from presidio_analyzer import AnalyzerEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


@dataclass(slots=True)
class PresidioDetectionResult:
    sanitized_text: str
    triggered: bool
    reason: str


@dataclass(slots=True)
class _PresidioRuntime:
    analyzer: Any
    anonymizer: Any


class PresidioPIIDetector:
    def __init__(
        self,
        *,
        entities: list[str],
        config_path: str | Path,
        language: str,
        allow_list: list[str] | None = None,
        score_threshold: float | None = None,
    ) -> None:
        self._entities = entities
        self._config_path = Path(config_path).resolve()
        self._language = language
        self._allow_list = allow_list or []
        self._score_threshold = score_threshold
        self._validated_entities: list[str] | None = None

    def analyze(self, text: str) -> PresidioDetectionResult:
        runtime = _load_presidio_runtime(str(self._config_path))
        entities = self._validated_entities or self._validate_entities(runtime.analyzer)
        analyzer_results = runtime.analyzer.analyze(
            text=text,
            language=self._language,
            entities=entities,
            allow_list=self._allow_list or None,
            score_threshold=self._score_threshold,
        )

        if not analyzer_results:
            return PresidioDetectionResult(
                sanitized_text=text,
                triggered=False,
                reason="No sensitive data detected.",
            )

        operators = {
            entity: self._build_operator_config(entity)
            for entity in {result.entity_type for result in analyzer_results}
        }
        sanitized = runtime.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators,
        )
        detected_entities = ", ".join(sorted({result.entity_type for result in analyzer_results}))
        return PresidioDetectionResult(
            sanitized_text=sanitized.text,
            triggered=True,
            reason=f"PII detected by Presidio: {detected_entities}.",
        )

    def _validate_entities(self, analyzer: Any) -> list[str]:
        try:
            supported_entities = set(analyzer.get_supported_entities(self._language))
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load Presidio entities for language '{self._language}'."
            ) from exc

        unsupported_entities: list[str] = []
        configured_entities: list[str] = []
        for entity in self._entities:
            if entity not in supported_entities:
                unsupported_entities.append(entity)
            else:
                configured_entities.append(entity)

        if unsupported_entities:
            supported = ", ".join(sorted(supported_entities))
            unsupported = ", ".join(sorted(unsupported_entities))
            raise RuntimeError(
                "Unsupported Presidio entities configured for "
                f"language '{self._language}': {unsupported}. "
                f"Supported by configured Presidio recognizers: {supported}."
            )

        self._validated_entities = configured_entities
        return configured_entities

    @staticmethod
    def _build_operator_config(entity: str) -> Any:
        return OperatorConfig("replace", {"new_value": f"<{entity}>"})


@lru_cache(maxsize=4)
def _load_presidio_runtime(config_path: str) -> _PresidioRuntime:
    resolved_path = Path(config_path)
    if not resolved_path.exists():
        raise RuntimeError(f"Presidio config file does not exist: {resolved_path}")

    try:
        analyzer = AnalyzerEngineProvider(analyzer_engine_conf_file=resolved_path).create_engine()
    except Exception as exc:
        raise RuntimeError(
            "Failed to initialize Presidio with config "
            f"{resolved_path}. Ensure the configured spaCy models are installed."
        ) from exc

    anonymizer = AnonymizerEngine()
    return _PresidioRuntime(analyzer=analyzer, anonymizer=anonymizer)


def build_test_runtime(*, analyzer: Any, anonymizer: Any | None = None) -> _PresidioRuntime:
    return _PresidioRuntime(
        analyzer=analyzer,
        anonymizer=anonymizer if anonymizer is not None else SimpleNamespace(),
    )
