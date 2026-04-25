"""Tracing sanitization helpers for secrets and sensitive content."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

from customer_bot.config import Settings

logger = logging.getLogger(__name__)

_MASK = "[redacted]"
_UNMASKED_KEYS = {
    "session_id",
    "request_id",
    "status",
    "guardrail_reason",
    "handoff_required",
    "retry_used",
    "tool_name",
    "faq_id",
    "score",
}
_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "token",
    "secret",
    "password",
}


def compile_secret_patterns(patterns: Sequence[str]) -> list[re.Pattern[str]]:
    """Compile the configured secret-detection regex patterns."""
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        compiled.append(re.compile(pattern, re.IGNORECASE))
    return compiled


def redact_text(
    value: str,
    *,
    patterns: Sequence[re.Pattern[str]],
    force: bool = False,
) -> tuple[str, bool]:
    """Redact matching secrets from a string and report whether it changed."""
    sanitized = value
    changed = False
    for pattern in patterns:
        next_value, replacements = pattern.subn(_MASK, sanitized)
        sanitized = next_value
        changed = changed or replacements > 0
    if force and sanitized:
        return (_MASK, True)
    return (sanitized, changed)


def sanitize_for_tracing(value: Any, settings: Settings) -> Any:
    """Sanitize arbitrary structured data before it is sent to tracing."""
    compiled = compile_secret_patterns(
        [
            *settings.guardrails.input.pii.custom_patterns,
            *settings.guardrails.output.pii.custom_patterns,
        ]
    )
    return _sanitize_value(value, (), compiled)


def build_langfuse_mask(settings: Settings):
    """Build the Langfuse-compatible masking callback used at client setup."""

    def _mask(*, data: Any = None, **kwargs: Any) -> Any:
        if kwargs:
            logger.debug("Langfuse mask received extra kwargs: %s", sorted(kwargs))
        value = data if data is not None else kwargs.get("value")
        return sanitize_for_tracing(value, settings)

    return _mask


def _sanitize_value(
    value: Any,
    path: tuple[str, ...],
    patterns: Sequence[re.Pattern[str]],
) -> Any:
    """Recursively sanitize nested mappings, sequences, and strings."""
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            # These keys are intentionally preserved because they carry routing,
            # status, or retrieval identity rather than sensitive content.
            if key_text in _UNMASKED_KEYS:
                sanitized[key_text] = item
                continue
            if key_text.lower() in _SENSITIVE_KEYS:
                sanitized[key_text] = _sanitize_value(item, (*path, key_text), patterns)
                continue
            if _looks_like_secret_key(key_text):
                sanitized[key_text] = _MASK
                continue
            sanitized[key_text] = _sanitize_value(item, (*path, key_text), patterns)
        return sanitized

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(item, path, patterns) for item in value]

    if isinstance(value, str):
        force = any(part.lower() in _SENSITIVE_KEYS for part in path)
        sanitized, _ = redact_text(value, patterns=patterns, force=force)
        return sanitized

    return value


def _looks_like_secret_key(key: str) -> bool:
    """Return whether a mapping key name itself implies secret content."""
    lowered = key.lower()
    return any(part in lowered for part in ("authorization", "token", "secret", "password"))
