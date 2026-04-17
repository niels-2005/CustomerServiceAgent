from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_NO_MATCH_INSTRUCTION = "If faq_lookup returns an empty matches list, explain in German that you could not find reliable information in the FAQs."
DEFAULT_ERROR_FALLBACK_TEXT = "Aktuell konnte ich die Informationen nicht zuverlässig abrufen, bitte später erneut versuchen oder den Support kontaktieren."
DEFAULT_AGENT_DESCRIPTION = "Agent for FAQ-only customer support responses"
DEFAULT_AGENT_SYSTEM_PROMPT = AGENT_SYSTEM_PROMPT = (
    "You are a customer support FAQ assistant. Use the faq_lookup tool whenever you need new FAQ information to answer the user's message. The tool returns JSON with matches where each item has faq_id, answer, and score. Write a concise German answer using only information grounded in tool results"
)
DEFAULT_FAQ_TOOL_DESCRIPTION = (
    "Find top FAQ matches for a user question after similarity filtering. "
    "Returns JSON with a `matches` list containing `faq_id`, `answer`, and `score`."
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
    ollama_chat_model: str = "qwen3.5:0.8b"
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
    no_match_instruction: str = DEFAULT_NO_MATCH_INSTRUCTION
    faq_tool_description: str = DEFAULT_FAQ_TOOL_DESCRIPTION
    agent_timeout_seconds: float | None = 500

    error_fallback_text: str = DEFAULT_ERROR_FALLBACK_TEXT

    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="http://localhost:3000", alias="LANGFUSE_HOST")
    langfuse_fail_fast: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
