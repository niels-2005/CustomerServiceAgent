"""Pydantic models for the public FastAPI request and response contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, StringConstraints, field_validator

from customer_bot.config import get_settings

UserMessage = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ChatRequest(BaseModel):
    """Incoming payload for ``POST /chat``."""

    user_message: UserMessage
    session_id: str | None = None

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, value: str) -> str:
        max_length = get_settings().api.max_user_message_length
        if len(value) > max_length:
            raise ValueError(f"user_message must be at most {max_length} characters long")
        return value

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class ChatResponse(BaseModel):
    """Normalized API response for one processed chat turn."""

    answer: str
    session_id: str
    trace_id: str | None = None
    status: Literal["answered", "blocked", "handoff", "fallback", "session_limit"]
    guardrail_reason: str | None = None
    handoff_required: bool
    retry_used: bool
    sanitized: bool


class ErrorDetails(BaseModel):
    """Machine-readable error payload returned by the API layer."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    """Top-level API error envelope."""

    error: ErrorDetails
    request_id: str


class HealthResponse(BaseModel):
    """Liveness response for ``GET /health``."""

    status: Literal["ok"] = "ok"
