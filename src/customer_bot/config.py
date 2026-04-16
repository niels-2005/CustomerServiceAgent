from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FALLBACK_TEXT = (
    "Dazu habe ich in unseren FAQs aktuell keine verlässliche Information. "
    "Bitte kontaktiere den Support direkt."
)
DEFAULT_AGENT_DESCRIPTION = "Agent for FAQ-only customer support responses"
DEFAULT_AGENT_SYSTEM_PROMPT = (
    "You are a customer support FAQ assistant. "
    "Always call the faq_lookup tool with the user question and "
    "return the tool output exactly as-is."
)
DEFAULT_FAQ_TOOL_DESCRIPTION = (
    "Find the best matching FAQ answer for a user question. Returns a plain German answer string."
)

TextIngestionMode = Literal["question_only", "answer_only", "question_answer"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen2.5:7b-instruct"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_request_timeout_seconds: float = 360.0
    ollama_thinking: bool = True
    ollama_context_window: int = 8000
    ollama_keep_alive: str | float | None = "10m"
    ollama_embedding_num_ctx: int | None = None

    chroma_persist_dir: Path = Path(".chroma")
    chroma_collection_name: str = "customer_bot_faq"
    corpus_csv_path: Path = Path("dataset/corpus.csv")
    text_ingestion_mode: TextIngestionMode = "question_only"

    retrieval_top_k: int = 3
    similarity_cutoff: float = 0.60

    memory_max_turns: int = 10
    agent_description: str = DEFAULT_AGENT_DESCRIPTION
    agent_system_prompt: str = DEFAULT_AGENT_SYSTEM_PROMPT
    faq_tool_description: str = DEFAULT_FAQ_TOOL_DESCRIPTION
    agent_timeout_seconds: float | None = 45.0

    fallback_text: str = DEFAULT_FALLBACK_TEXT

    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="http://localhost:3000", alias="LANGFUSE_HOST")
    langfuse_fail_fast: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
