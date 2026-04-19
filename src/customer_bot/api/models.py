from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, StringConstraints, field_validator

from customer_bot.config import get_settings

UserMessage = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ChatRequest(BaseModel):
    user_message: UserMessage
    session_id: str | None = None

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, value: str) -> str:
        max_length = get_settings().api_max_user_message_length
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
    answer: str
    session_id: str


class ErrorDetails(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetails
    request_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
