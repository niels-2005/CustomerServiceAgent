"""Shared SlowAPI limiter instance and configuration helpers.

The API routes are decorated against a module-level limiter instance, so app
startup reconfigures that singleton from runtime settings before the FastAPI app
starts serving requests.
"""

from __future__ import annotations

from fastapi import Request
from limits.storage import storage_from_string
from limits.strategies import STRATEGIES
from slowapi import Limiter
from slowapi.extension import LimitGroup
from slowapi.util import get_remote_address

from customer_bot.config import Settings


def get_rate_limit_key(request: Request) -> str:
    """Resolve the client identifier used for rate limiting.

    The default deployment talks directly to Uvicorn, so the peer address is the
    trusted source of identity. Forwarded headers are only considered when the
    runtime settings opt into that behavior explicitly.
    """

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and _proxy_headers_are_trusted():
        client_ip = forwarded_for.split(",", maxsplit=1)[0].strip()
        if client_ip:
            return client_ip
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key, headers_enabled=False)


def configure_limiter(settings: Settings) -> None:
    """Apply runtime rate-limit settings to the shared SlowAPI limiter."""

    rate_limit_settings = settings.api.rate_limit
    limiter.enabled = rate_limit_settings.enabled
    limiter._headers_enabled = rate_limit_settings.headers_enabled
    limiter._key_prefix = rate_limit_settings.key_prefix
    limiter._default_limits = [
        LimitGroup(
            rate_limit_settings.default_limit,
            limiter._key_func,
            None,
            False,
            None,
            None,
            None,
            1,
            False,
        )
    ]

    storage_uri = rate_limit_settings.storage_uri
    assert storage_uri is not None
    if storage_uri != limiter._storage_uri:
        limiter._storage_uri = storage_uri
        limiter._storage = storage_from_string(storage_uri, **limiter._storage_options)
        strategy = limiter._strategy or "fixed-window"
        limiter._limiter = STRATEGIES[strategy](limiter._storage)


def validate_rate_limit_storage(settings: Settings) -> None:
    """Fail fast when the configured rate-limit backend is unavailable."""

    storage_uri = settings.api.rate_limit.storage_uri
    assert storage_uri is not None
    if not limiter._storage.check():
        msg = f"Rate limit storage backend is unavailable: {storage_uri}"
        raise RuntimeError(msg)


def _proxy_headers_are_trusted() -> bool:
    """Resolve the proxy-header trust flag lazily from runtime settings."""
    from customer_bot.api.deps import get_runtime_settings

    return get_runtime_settings().api.rate_limit.trust_proxy_headers
