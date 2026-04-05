from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from opentelemetry import trace

from customer_bot.api.deps import get_chat_service
from customer_bot.api.models import ChatRequest, ChatResponse, HealthResponse
from customer_bot.chat.service import ChatService

router = APIRouter()
tracer = trace.get_tracer("customer_bot.api")

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, chat_service: ChatServiceDep) -> ChatResponse:
    with tracer.start_as_current_span("chat_endpoint") as span:
        span.set_attribute("endpoint", "/chat")
        if payload.session_id:
            span.set_attribute("session.id", payload.session_id)

        result = await chat_service.chat(
            user_message=payload.user_message,
            session_id=payload.session_id,
        )

        span.set_attribute("session.id", result.session_id)
        return ChatResponse(answer=result.answer, session_id=result.session_id)
