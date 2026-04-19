from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_NO_MATCH_INSTRUCTION = (
    "If faq_lookup returns an empty matches list, explain in German that you "
    "could not find reliable information in the FAQs."
)
DEFAULT_ERROR_FALLBACK_TEXT = (
    "Aktuell konnte ich die Informationen nicht zuverlässig abrufen, bitte "
    "später erneut versuchen oder den Support kontaktieren."
)
DEFAULT_AGENT_DESCRIPTION = "Agent for FAQ-only customer support responses"
DEFAULT_AGENT_SYSTEM_PROMPT = AGENT_SYSTEM_PROMPT = (
    "You are a customer support FAQ assistant. Use the faq_lookup tool "
    "whenever you need new FAQ information to answer the user's message. "
    "The tool returns JSON with matches where each item has faq_id, answer, "
    "and score. Write a concise German answer using only information "
    "grounded in tool results"
)
DEFAULT_FAQ_TOOL_DESCRIPTION = (
    "Find top FAQ matches for a user question after similarity filtering. "
    "Returns JSON with a `matches` list containing `faq_id`, `answer`, and `score`."
)

TextIngestionMode = Literal["question_only", "answer_only", "question_answer"]
LlmProvider = Literal["ollama", "openai", "gemini", "openrouter"]
EmbeddingProvider = Literal["ollama", "openai", "gemini"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    llm_provider: LlmProvider = "ollama"
    embedding_provider: EmbeddingProvider = "ollama"

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_llm_model: str = "gpt-4o-mini"
    openai_llm_temperature: float | None = None
    openai_llm_max_tokens: int | None = None
    openai_llm_max_retries: int | None = None
    openai_llm_timeout_seconds: float | None = None
    openai_llm_api_base: str | None = None
    openai_llm_api_version: str | None = None
    openai_llm_strict: bool | None = None
    openai_llm_reasoning_effort: (
        Literal["none", "minimal", "low", "medium", "high", "xhigh"] | None
    ) = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_mode: str | None = None
    openai_embedding_batch_size: int | None = None
    openai_embedding_dimensions: int | None = None
    openai_embedding_max_retries: int | None = None
    openai_embedding_timeout_seconds: float | None = None
    openai_embedding_api_base: str | None = None
    openai_embedding_api_version: str | None = None
    openai_embedding_num_workers: int | None = None

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_llm_model: str = "gemini-2.5-flash"
    gemini_llm_temperature: float | None = None
    gemini_llm_max_tokens: int | None = None
    gemini_llm_context_window: int | None = None
    gemini_llm_max_retries: int | None = None
    gemini_llm_cached_content: str | None = None
    gemini_llm_file_mode: Literal["inline", "fileapi", "hybrid"] | None = None
    gemini_embedding_model: str = "gemini-embedding-2-preview"
    gemini_embedding_batch_size: int | None = None
    gemini_embedding_retries: int | None = None
    gemini_embedding_timeout_seconds: int | None = None
    gemini_embedding_retry_min_seconds: float | None = None
    gemini_embedding_retry_max_seconds: float | None = None
    gemini_embedding_retry_exponential_base: float | None = None

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_llm_model: str = "mistralai/mixtral-8x7b-instruct"
    openrouter_temperature: float | None = None
    openrouter_max_tokens: int | None = None
    openrouter_context_window: int | None = None
    openrouter_max_retries: int | None = None
    openrouter_api_base: str | None = None
    openrouter_allow_fallbacks: bool | None = None

    ollama_base_url: str | None = None
    ollama_chat_model: str = "qwen3.5:9b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    ollama_temperature: float | None = None
    ollama_request_timeout_seconds: float | None = None
    ollama_prompt_key: str | None = None
    ollama_json_mode: bool | None = None
    ollama_thinking: bool | Literal["low", "medium", "high"] | None = None
    ollama_context_window: int | None = None
    ollama_keep_alive: str | float | None = None
    ollama_embedding_batch_size: int | None = None
    ollama_embedding_keep_alive: str | float | None = None
    ollama_embedding_query_instruction: str | None = None
    ollama_embedding_text_instruction: str | None = None
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
    langfuse_tracing_environment: str = Field(
        default="default", alias="LANGFUSE_TRACING_ENVIRONMENT"
    )
    langfuse_release: str = Field(default="", alias="LANGFUSE_RELEASE")
    langfuse_fail_fast: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
