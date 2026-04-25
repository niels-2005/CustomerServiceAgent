"""Typed configuration models loaded from environment and default YAML files.

The models group related runtime settings so provider selection, retrieval,
guardrails, and API behavior remain explicit and validated at startup.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TextIngestionMode = Literal["question_only", "answer_only", "question_answer"]
LlmProvider = Literal["ollama", "openai"]
EmbeddingProvider = Literal["ollama", "openai"]
GuardrailProvider = Literal["openai"]
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ApiConfig(ConfigModel):
    host: str
    port: int
    max_user_message_length: int
    cors_allow_origins: list[str]
    cors_allow_credentials: bool
    cors_allow_methods: list[str]
    cors_allow_headers: list[str]
    trusted_hosts: list[str]
    chat_rate_limit: str


class ProviderSelectors(ConfigModel):
    llm: LlmProvider
    embedding: EmbeddingProvider
    guardrail: GuardrailProvider


class OllamaLlmConfig(ConfigModel):
    chat_model: str
    base_url: str | None
    request_timeout_seconds: float | None
    thinking: bool | Literal["low", "medium", "high"] | None
    context_window: int | None
    temperature: float | None
    prompt_key: str | None
    json_mode: bool | None
    keep_alive: str | float | None


class OpenAILlmConfig(ConfigModel):
    model: str
    temperature: float | None
    max_completion_tokens: int | None
    max_retries: int | None
    timeout_seconds: float | None
    api_base: str | None
    api_version: str | None
    strict: bool | None
    reasoning_effort: ReasoningEffort | None


class LlmConfig(ConfigModel):
    ollama: OllamaLlmConfig
    openai: OpenAILlmConfig


class OllamaEmbeddingConfig(ConfigModel):
    model: str
    batch_size: int | None
    keep_alive: str | float | None
    query_instruction: str | None
    text_instruction: str | None
    num_ctx: int | None


class OpenAIEmbeddingConfig(ConfigModel):
    model: str
    mode: str | None
    batch_size: int | None
    dimensions: int | None
    max_retries: int | None
    timeout_seconds: float | None
    api_base: str | None
    api_version: str | None
    num_workers: int | None


class EmbeddingConfig(ConfigModel):
    ollama: OllamaEmbeddingConfig
    openai: OpenAIEmbeddingConfig


class OpenAIGuardrailConfig(ConfigModel):
    model: str
    temperature: float | None
    max_completion_tokens: int | None
    max_retries: int | None
    timeout_seconds: float | None
    api_base: str | None
    api_version: str | None
    strict: bool | None
    reasoning_effort: ReasoningEffort | None


class GuardrailConfig(ConfigModel):
    openai: OpenAIGuardrailConfig


class StorageCollectionConfig(ConfigModel):
    collection_name: str


class StorageConfig(ConfigModel):
    chroma_persist_dir: Path
    faq: StorageCollectionConfig
    products: StorageCollectionConfig


class FaqIngestionConfig(ConfigModel):
    corpus_csv_path: Path
    text_ingestion_mode: TextIngestionMode


class ProductsIngestionConfig(ConfigModel):
    corpus_csv_path: Path


class IngestionConfig(ConfigModel):
    faq: FaqIngestionConfig
    products: ProductsIngestionConfig


class RetrievalSourceConfig(ConfigModel):
    top_k: int
    similarity_cutoff: float


class RetrievalConfig(ConfigModel):
    faq: RetrievalSourceConfig
    products: RetrievalSourceConfig


class MemoryConfig(ConfigModel):
    max_turns: int


class AgentConfig(ConfigModel):
    agent_description: str
    agent_system_prompt: str
    agent_timeout_seconds: float | None


class MessagesConfig(ConfigModel):
    employee_request_instruction: str
    no_match_instruction: str
    faq_tool_description: str
    product_tool_description: str
    error_fallback_text: str


class GuardrailsGlobalConfig(ConfigModel):
    enabled: bool
    fail_closed: bool
    max_output_retries: int


class GuardrailsTracingConfig(ConfigModel):
    inputs: bool
    outputs: bool
    include_config: bool


class GuardrailsPiiConfig(ConfigModel):
    enabled: bool
    presidio_config_path: Path
    presidio_language: str
    presidio_allow_list: list[str]
    presidio_score_threshold: float
    entities: list[str]
    custom_patterns: list[str]
    message: str


class GuardrailsPromptInjectionConfig(ConfigModel):
    enabled: bool
    heuristic_terms: list[str]
    system_prompt: str
    user_prompt_template: str
    message: str


class GuardrailsTopicRelevanceConfig(ConfigModel):
    enabled: bool
    allowed_domain_hints: list[str]
    system_prompt: str
    user_prompt_template: str
    message: str
    help_text: str


class GuardrailsEscalationConfig(ConfigModel):
    enabled: bool
    heuristic_terms: list[str]
    system_prompt: str
    user_prompt_template: str
    message: str


class GuardrailsInputConfig(ConfigModel):
    pii: GuardrailsPiiConfig
    prompt_injection: GuardrailsPromptInjectionConfig
    topic_relevance: GuardrailsTopicRelevanceConfig
    escalation: GuardrailsEscalationConfig


class GuardrailsOutputPiiConfig(ConfigModel):
    enabled: bool
    entities: list[str]
    custom_patterns: list[str]


class GuardrailsGroundingConfig(ConfigModel):
    enabled: bool
    system_prompt: str
    user_prompt_template: str


class GuardrailsBiasConfig(ConfigModel):
    enabled: bool
    bias_terms: list[str]
    system_prompt: str
    user_prompt_template: str


class GuardrailsRewriteConfig(ConfigModel):
    enabled: bool
    system_prompt: str
    user_prompt_template: str


class GuardrailsOutputConfig(ConfigModel):
    pii: GuardrailsOutputPiiConfig
    grounding: GuardrailsGroundingConfig
    bias: GuardrailsBiasConfig
    rewrite: GuardrailsRewriteConfig


class GuardrailsConfig(ConfigModel):
    global_: GuardrailsGlobalConfig = Field(alias="global")
    tracing: GuardrailsTracingConfig
    input: GuardrailsInputConfig
    output: GuardrailsOutputConfig


class LangfuseConfig(ConfigModel):
    host: str
    tracing_environment: str
    release: str
    fail_fast: bool
