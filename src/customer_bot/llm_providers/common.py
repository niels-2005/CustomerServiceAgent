from __future__ import annotations

from typing import Any


def require_api_key(*, provider: str, env_var: str, value: str) -> str:
    normalized = value.strip()
    if normalized:
        return normalized
    raise ValueError(f"Missing required API key for provider '{provider}'. Set {env_var}.")


def compact_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and value != "" and not (isinstance(value, dict) and not value)
    }
