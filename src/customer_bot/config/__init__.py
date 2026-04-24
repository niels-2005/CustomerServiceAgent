from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

TextIngestionMode = Literal["question_only", "answer_only", "question_answer"]
LlmProvider = Literal["ollama", "openai"]
EmbeddingProvider = Literal["ollama", "openai"]
GuardrailProvider = Literal["openai"]
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


def _default_yaml_files() -> tuple[Path, ...]:
    defaults_dir = Path(__file__).resolve().parent / "defaults"
    return (
        defaults_dir / "api.yaml",
        defaults_dir / "providers.yaml",
        defaults_dir / "retrieval.yaml",
        defaults_dir / "agent.yaml",
        defaults_dir / "guardrails.yaml",
        defaults_dir / "observability.yaml",
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_sources = tuple(
            YamlConfigSettingsSource(settings_cls, yaml_file=path) for path in _default_yaml_files()
        )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            *yaml_sources,
            file_secret_settings,
        )

    api_host: str
    api_port: int
    api_max_user_message_length: int
    api_cors_allow_origins: list[str]
    api_cors_allow_credentials: bool
    api_cors_allow_methods: list[str]
    api_cors_allow_headers: list[str]
    api_trusted_hosts: list[str]
    api_chat_rate_limit: str

    llm_provider: LlmProvider
    embedding_provider: EmbeddingProvider
    guardrail_provider: GuardrailProvider

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    ollama_base_url: str | None
    ollama_chat_model: str
    ollama_embedding_model: str
    ollama_temperature: float | None
    ollama_request_timeout_seconds: float | None
    ollama_prompt_key: str | None
    ollama_json_mode: bool | None
    ollama_thinking: bool | Literal["low", "medium", "high"] | None
    ollama_context_window: int | None
    ollama_keep_alive: str | float | None
    ollama_embedding_batch_size: int | None
    ollama_embedding_keep_alive: str | float | None
    ollama_embedding_query_instruction: str | None
    ollama_embedding_text_instruction: str | None
    ollama_embedding_num_ctx: int | None

    openai_llm_model: str
    openai_llm_temperature: float | None
    openai_llm_max_completion_tokens: int | None
    openai_llm_max_retries: int | None
    openai_llm_timeout_seconds: float | None
    openai_llm_api_base: str | None
    openai_llm_api_version: str | None
    openai_llm_strict: bool | None
    openai_llm_reasoning_effort: ReasoningEffort | None

    openai_embedding_model: str
    openai_embedding_mode: str | None
    openai_embedding_batch_size: int | None
    openai_embedding_dimensions: int | None
    openai_embedding_max_retries: int | None
    openai_embedding_timeout_seconds: float | None
    openai_embedding_api_base: str | None
    openai_embedding_api_version: str | None
    openai_embedding_num_workers: int | None

    openai_guardrail_model: str
    openai_guardrail_temperature: float | None
    openai_guardrail_max_completion_tokens: int | None
    openai_guardrail_max_retries: int | None
    openai_guardrail_timeout_seconds: float | None
    openai_guardrail_api_base: str | None
    openai_guardrail_api_version: str | None
    openai_guardrail_strict: bool | None
    openai_guardrail_reasoning_effort: ReasoningEffort | None

    chroma_persist_dir: Path
    faq_collection_name: str
    products_collection_name: str
    faq_corpus_csv_path: Path
    products_corpus_csv_path: Path
    faq_text_ingestion_mode: TextIngestionMode
    faq_retrieval_top_k: int
    faq_similarity_cutoff: float
    products_retrieval_top_k: int
    products_similarity_cutoff: float
    memory_max_turns: int

    agent_description: str
    agent_system_prompt: str
    no_match_instruction: str
    faq_tool_description: str
    product_no_match_instruction: str
    product_tool_description: str
    agent_timeout_seconds: float | None
    error_fallback_text: str

    guardrails_enabled: bool
    guardrails_fail_closed: bool
    guardrails_max_output_retries: int
    guardrails_trace_inputs: bool
    guardrails_trace_outputs: bool
    guardrails_trace_include_config: bool

    guardrails_input_pii_enabled: bool
    guardrails_presidio_config_path: Path
    guardrails_presidio_language: str
    guardrails_presidio_allow_list: list[str]
    guardrails_presidio_score_threshold: float
    guardrails_input_pii_entities: list[str]
    guardrails_input_pii_custom_patterns: list[str]
    guardrails_input_pii_message: str

    guardrails_prompt_injection_enabled: bool
    guardrails_prompt_injection_system_prompt: str
    guardrails_prompt_injection_user_prompt_template: str
    guardrails_prompt_injection_message: str
    guardrails_prompt_injection_heuristic_terms: list[str]

    guardrails_topic_relevance_enabled: bool
    guardrails_topic_relevance_system_prompt: str
    guardrails_topic_relevance_user_prompt_template: str
    guardrails_topic_relevance_message: str
    guardrails_topic_relevance_help_text: str
    guardrails_topic_allowed_terms: list[str]

    guardrails_escalation_enabled: bool
    guardrails_escalation_system_prompt: str
    guardrails_escalation_user_prompt_template: str
    guardrails_escalation_message: str
    guardrails_escalation_heuristic_terms: list[str]

    guardrails_output_pii_enabled: bool
    guardrails_output_pii_entities: list[str]
    guardrails_output_pii_custom_patterns: list[str]

    guardrails_grounding_enabled: bool
    guardrails_grounding_system_prompt: str
    guardrails_grounding_user_prompt_template: str

    guardrails_bias_enabled: bool
    guardrails_bias_system_prompt: str
    guardrails_bias_user_prompt_template: str
    guardrails_bias_heuristic_terms: list[str]

    guardrails_rewrite_enabled: bool
    guardrails_rewrite_system_prompt: str
    guardrails_rewrite_user_prompt_template: str

    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(alias="LANGFUSE_HOST")
    langfuse_tracing_environment: str = Field(alias="LANGFUSE_TRACING_ENVIRONMENT")
    langfuse_release: str = Field(alias="LANGFUSE_RELEASE")
    langfuse_fail_fast: bool

    @model_validator(mode="before")
    @classmethod
    def _flatten_nested_yaml_sections(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        payload = dict(data)

        def merge(prefixed_values: dict[str, object | None]) -> None:
            for key, value in prefixed_values.items():
                payload.setdefault(key, value)

        def prefixed(section: dict[str, object], prefix: str) -> dict[str, object]:
            return {f"{prefix}{key}": value for key, value in section.items()}

        selectors = payload.pop("selectors", None)
        if isinstance(selectors, dict):
            merge(
                {
                    "llm_provider": selectors.get("llm"),
                    "embedding_provider": selectors.get("embedding"),
                    "guardrail_provider": selectors.get("guardrail"),
                }
            )

        llm = payload.pop("llm", None)
        if isinstance(llm, dict):
            if isinstance(llm.get("ollama"), dict):
                merge(prefixed(llm["ollama"], "ollama_"))
            if isinstance(llm.get("openai"), dict):
                merge(prefixed(llm["openai"], "openai_llm_"))

        embedding = payload.pop("embedding", None)
        if isinstance(embedding, dict):
            if isinstance(embedding.get("ollama"), dict):
                merge(prefixed(embedding["ollama"], "ollama_embedding_"))
            if isinstance(embedding.get("openai"), dict):
                merge(prefixed(embedding["openai"], "openai_embedding_"))

        guardrail = payload.pop("guardrail", None)
        if isinstance(guardrail, dict) and isinstance(guardrail.get("openai"), dict):
            merge(prefixed(guardrail["openai"], "openai_guardrail_"))

        storage = payload.pop("storage", None)
        if isinstance(storage, dict):
            merge({"chroma_persist_dir": storage.get("chroma_persist_dir")})
            if isinstance(storage.get("faq"), dict):
                merge({"faq_collection_name": storage["faq"].get("collection_name")})
            if isinstance(storage.get("products"), dict):
                merge({"products_collection_name": storage["products"].get("collection_name")})

        ingestion = payload.pop("ingestion", None)
        if isinstance(ingestion, dict):
            if isinstance(ingestion.get("faq"), dict):
                merge(
                    {
                        "faq_corpus_csv_path": ingestion["faq"].get("corpus_csv_path"),
                        "faq_text_ingestion_mode": ingestion["faq"].get("text_ingestion_mode"),
                    }
                )
            if isinstance(ingestion.get("products"), dict):
                merge(
                    {
                        "products_corpus_csv_path": ingestion["products"].get("corpus_csv_path"),
                    }
                )

        retrieval = payload.pop("retrieval", None)
        if isinstance(retrieval, dict):
            if isinstance(retrieval.get("faq"), dict):
                merge(
                    {
                        "faq_retrieval_top_k": retrieval["faq"].get("top_k"),
                        "faq_similarity_cutoff": retrieval["faq"].get("similarity_cutoff"),
                    }
                )
            if isinstance(retrieval.get("products"), dict):
                merge(
                    {
                        "products_retrieval_top_k": retrieval["products"].get("top_k"),
                        "products_similarity_cutoff": retrieval["products"].get(
                            "similarity_cutoff"
                        ),
                    }
                )

        memory = payload.pop("memory", None)
        if isinstance(memory, dict):
            merge({"memory_max_turns": memory.get("max_turns")})

        agent = payload.pop("agent", None)
        if isinstance(agent, dict):
            merge(agent)

        messages = payload.pop("messages", None)
        if isinstance(messages, dict):
            merge(messages)

        langfuse = payload.pop("langfuse", None)
        if isinstance(langfuse, dict):
            merge(prefixed(langfuse, "langfuse_"))

        guardrails = payload.pop("guardrails", None)
        if isinstance(guardrails, dict):
            if isinstance(guardrails.get("global"), dict):
                merge(prefixed(guardrails["global"], "guardrails_"))
            if isinstance(guardrails.get("tracing"), dict):
                merge(prefixed(guardrails["tracing"], "guardrails_trace_"))

            input_guardrails = guardrails.get("input")
            if isinstance(input_guardrails, dict):
                if isinstance(input_guardrails.get("pii"), dict):
                    pii = dict(input_guardrails["pii"])
                    merge(
                        {
                            "guardrails_input_pii_enabled": pii.pop("enabled", None),
                            "guardrails_presidio_config_path": pii.pop(
                                "presidio_config_path", None
                            ),
                            "guardrails_presidio_language": pii.pop("presidio_language", None),
                            "guardrails_presidio_allow_list": pii.pop("presidio_allow_list", None),
                            "guardrails_presidio_score_threshold": pii.pop(
                                "presidio_score_threshold", None
                            ),
                            "guardrails_input_pii_entities": pii.pop("entities", None),
                            "guardrails_input_pii_custom_patterns": pii.pop(
                                "custom_patterns", None
                            ),
                            "guardrails_input_pii_message": pii.pop("message", None),
                        }
                    )
                if isinstance(input_guardrails.get("prompt_injection"), dict):
                    merge(
                        {
                            f"guardrails_prompt_injection_{key}": value
                            for key, value in input_guardrails["prompt_injection"].items()
                        }
                    )
                if isinstance(input_guardrails.get("topic_relevance"), dict):
                    section = dict(input_guardrails["topic_relevance"])
                    merge(
                        {
                            "guardrails_topic_relevance_enabled": section.pop("enabled", None),
                            "guardrails_topic_allowed_terms": section.pop("allowed_terms", None),
                            "guardrails_topic_relevance_system_prompt": section.pop(
                                "system_prompt", None
                            ),
                            "guardrails_topic_relevance_user_prompt_template": section.pop(
                                "user_prompt_template", None
                            ),
                            "guardrails_topic_relevance_message": section.pop("message", None),
                            "guardrails_topic_relevance_help_text": section.pop("help_text", None),
                        }
                    )
                if isinstance(input_guardrails.get("escalation"), dict):
                    merge(
                        {
                            f"guardrails_escalation_{key}": value
                            for key, value in input_guardrails["escalation"].items()
                        }
                    )

            output_guardrails = guardrails.get("output")
            if isinstance(output_guardrails, dict):
                if isinstance(output_guardrails.get("pii"), dict):
                    section = dict(output_guardrails["pii"])
                    merge(
                        {
                            "guardrails_output_pii_enabled": section.pop("enabled", None),
                            "guardrails_output_pii_entities": section.pop("entities", None),
                            "guardrails_output_pii_custom_patterns": section.pop(
                                "custom_patterns", None
                            ),
                        }
                    )
                if isinstance(output_guardrails.get("grounding"), dict):
                    merge(
                        {
                            f"guardrails_grounding_{key}": value
                            for key, value in output_guardrails["grounding"].items()
                        }
                    )
                if isinstance(output_guardrails.get("bias"), dict):
                    merge(
                        {
                            f"guardrails_bias_{key}": value
                            for key, value in output_guardrails["bias"].items()
                        }
                    )
                if isinstance(output_guardrails.get("rewrite"), dict):
                    merge(
                        {
                            f"guardrails_rewrite_{key}": value
                            for key, value in output_guardrails["rewrite"].items()
                        }
                    )

        return payload


if TYPE_CHECKING:

    def _build_settings() -> Settings: ...

else:

    def _build_settings() -> Settings:
        return Settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _build_settings()
