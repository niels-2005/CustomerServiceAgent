from __future__ import annotations

import logging

from customer_bot.config import Settings
from customer_bot.guardrails.models import GuardrailCheck
from customer_bot.guardrails.presidio import PresidioPIIDetector
from customer_bot.guardrails.sanitization import compile_secret_patterns, redact_text

logger = logging.getLogger(__name__)


class _BasePiiGuard:
    def __init__(
        self,
        *,
        settings: Settings,
        entities: list[str],
        patterns: list[str],
        name: str,
    ) -> None:
        self._settings = settings
        self._entities = entities
        self._compiled_patterns = compile_secret_patterns(patterns)
        self._name = name
        self._detector: PresidioPIIDetector | None = None

    async def check(self, text: str) -> tuple[bool, str, GuardrailCheck]:
        sanitized, matched_secret = redact_text(text, patterns=self._compiled_patterns)
        if matched_secret:
            logger.warning("PII guard matched custom secret pattern: guard=%s", self._name)
            return (
                True,
                sanitized,
                GuardrailCheck(
                    name=self._name,
                    decision="block",
                    reason="Secret-like pattern detected.",
                    triggered=True,
                    decision_source="pii_detector",
                    llm_called=False,
                ),
            )

        logger.debug(
            "Running Presidio PII detection: guard=%s entities=%s",
            self._name,
            self._entities,
        )
        try:
            detection_result = self._detect_with_presidio(text)
        except Exception as exc:
            logger.warning(
                "Presidio PII detection failed: guard=%s error_type=%s error=%s",
                self._name,
                type(exc).__name__,
                exc,
            )
            raise RuntimeError("Presidio PII detection is unavailable.") from exc

        if detection_result.triggered:
            return (
                True,
                detection_result.sanitized_text,
                GuardrailCheck(
                    name=self._name,
                    decision="block",
                    reason=detection_result.reason,
                    triggered=True,
                    decision_source="pii_detector",
                    llm_called=False,
                ),
            )

        return (
            False,
            detection_result.sanitized_text,
            GuardrailCheck(
                name=self._name,
                decision="allow",
                reason=detection_result.reason,
                decision_source="pii_detector",
                llm_called=False,
            ),
        )

    def _detect_with_presidio(self, text: str):
        if self._detector is None:
            self._detector = PresidioPIIDetector(
                entities=self._entities,
                config_path=self._settings.guardrails_presidio_config_path,
                language=self._settings.guardrails_presidio_language,
                allow_list=self._settings.guardrails_presidio_allow_list,
                score_threshold=self._settings.guardrails_presidio_score_threshold,
            )
        return self._detector.analyze(text)


class SecretPIIGuard(_BasePiiGuard):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            entities=settings.guardrails_input_pii_entities,
            patterns=settings.guardrails_input_pii_custom_patterns,
            name="secret_pii",
        )


class OutputSensitiveDataGuard(_BasePiiGuard):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            entities=settings.guardrails_output_pii_entities,
            patterns=settings.guardrails_output_pii_custom_patterns,
            name="output_sensitive_data",
        )
