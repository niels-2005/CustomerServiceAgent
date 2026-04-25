"""Observability bootstrap for OpenInference and Langfuse."""

from __future__ import annotations

import logging

from langfuse import Langfuse
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

from customer_bot.config import Settings
from customer_bot.guardrails.sanitization import build_langfuse_mask

logger = logging.getLogger(__name__)

_INSTRUMENTED = False


def initialize_observability(settings: Settings) -> Langfuse | None:
    """Initialize tracing and return the Langfuse client when available.

    OpenInference instrumentation is installed at most once per process. The
    Langfuse client is optional and can fail fast or degrade gracefully based on
    configuration.
    """
    global _INSTRUMENTED

    if not _INSTRUMENTED:
        # Instrumentation is process-wide and should not be registered twice.
        LlamaIndexInstrumentor().instrument()
        _INSTRUMENTED = True

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        message = "Langfuse keys are missing. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY."
        if settings.langfuse.fail_fast:
            raise RuntimeError(message)
        logger.warning(message)
        return None

    client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse.host,
        environment=settings.langfuse.tracing_environment,
        release=settings.langfuse.release or None,
        mask=build_langfuse_mask(settings),
    )

    try:
        is_authorized = client.auth_check()
    except Exception as exc:  # pragma: no cover - depends on runtime availability
        # Connectivity can fail even when configuration is present; fail-fast
        # decides whether startup aborts or the app continues with partial tracing.
        if settings.langfuse.fail_fast:
            raise RuntimeError("Langfuse auth/connectivity check failed") from exc
        logger.warning("Langfuse auth/connectivity check failed: %s", exc)
        return client

    if not is_authorized:
        message = "Langfuse credentials are invalid or host is unreachable."
        if settings.langfuse.fail_fast:
            raise RuntimeError(message)
        logger.warning(message)

    return client
