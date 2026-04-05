from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    user_message: str = Field(min_length=1)
    session_id: str | None = Field(default=None, min_length=1)

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("user_message must not be blank")
        return normalized


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
