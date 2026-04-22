from __future__ import annotations

import importlib
import logging

from customer_bot.config import Settings
from customer_bot.guardrails.models import GuardrailCheck
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
                ),
            )

        detect_pii = self._load_detect_pii()
        if detect_pii is None:
            return (
                False,
                sanitized,
                GuardrailCheck(name=self._name, decision="allow", reason="PII guard disabled."),
            )

        from guardrails import Guard

        logger.debug(
            "Running DetectPII validator: guard=%s entities=%s",
            self._name,
            self._entities,
        )
        guard = Guard().use(
            detect_pii(pii_entities=self._entities, on_fail="exception"),
        )
        try:
            guard.validate(text)
        except Exception as exc:
            sanitized = self._redact_presidio_message(text)
            logger.warning(
                "DetectPII validation blocked content: guard=%s error_type=%s error=%s",
                self._name,
                type(exc).__name__,
                exc,
            )
            return (
                True,
                sanitized,
                GuardrailCheck(
                    name=self._name,
                    decision="block",
                    reason=str(exc),
                    triggered=True,
                ),
            )

        return (
            False,
            sanitized,
            GuardrailCheck(name=self._name, decision="allow", reason="No sensitive data detected."),
        )

    def _load_detect_pii(self):
        try:
            module = importlib.import_module("guardrails.hub")
        except Exception as exc:  # pragma: no cover - import failure depends on env
            logger.exception("Failed to import guardrails.hub for guard=%s", self._name)
            raise RuntimeError("guardrails.hub is unavailable.") from exc

        detect_pii = getattr(module, "DetectPII", None)
        if detect_pii is None:
            logger.error("DetectPII validator missing for guard=%s", self._name)
            raise RuntimeError(
                "DetectPII is not installed. Run "
                "`guardrails hub install hub://guardrails/detect_pii` after "
                "`guardrails configure`."
            )
        logger.debug("DetectPII validator loaded for guard=%s", self._name)
        return detect_pii

    def _redact_presidio_message(self, text: str) -> str:
        sanitized = text
        for pattern in self._compiled_patterns:
            sanitized = pattern.sub("[redacted]", sanitized)
        return sanitized


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
