"""Runtime settings loading and compatibility helpers.

Settings are assembled from environment variables, `.env`, and the default YAML
files in `config/defaults/`, with environment values taking precedence.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from customer_bot.config.models import (
    AgentConfig,
    ApiConfig,
    EmbeddingConfig,
    GuardrailConfig,
    GuardrailsConfig,
    IngestionConfig,
    LangfuseConfig,
    LlmConfig,
    MemoryConfig,
    MessagesConfig,
    ProviderSelectors,
    RetrievalConfig,
    StorageConfig,
)
from customer_bot.config.models import (
    EmbeddingProvider as EmbeddingProvider,
)
from customer_bot.config.models import (
    GuardrailProvider as GuardrailProvider,
)
from customer_bot.config.models import (
    LlmProvider as LlmProvider,
)
from customer_bot.config.models import (
    TextIngestionMode as TextIngestionMode,
)


def _default_yaml_files() -> tuple[Path, ...]:
    """Return the ordered default YAML files used for settings assembly."""
    defaults_dir = Path(__file__).resolve().parent / "defaults"
    return (
        defaults_dir / "api.yaml",
        defaults_dir / "providers.yaml",
        defaults_dir / "retrieval.yaml",
        defaults_dir / "memory.yaml",
        defaults_dir / "agent.yaml",
        defaults_dir / "guardrails.yaml",
        defaults_dir / "observability.yaml",
    )


class Settings(BaseSettings):
    """Validated application settings composed from env and default YAML files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_nested_delimiter="__",
    )

    api: ApiConfig
    selectors: ProviderSelectors
    llm: LlmConfig
    embedding: EmbeddingConfig
    guardrail: GuardrailConfig
    storage: StorageConfig
    ingestion: IngestionConfig
    retrieval: RetrievalConfig
    memory: MemoryConfig
    agent: AgentConfig
    messages: MessagesConfig
    guardrails: GuardrailsConfig = Field(alias="guardrails")
    langfuse: LangfuseConfig

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    rate_limit_redis_url: str | None = Field(
        default=None, alias="RATE_LIMIT_REDIS_URL", exclude=True
    )
    chat_memory_redis_url: str | None = Field(
        default=None,
        alias="CHAT_MEMORY_REDIS_URL",
        exclude=True,
    )
    langfuse_host_override: str | None = Field(default=None, alias="LANGFUSE_HOST", exclude=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Insert the repository's YAML defaults behind env-based sources."""
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

    @model_validator(mode="after")
    def _apply_env_compatibility_overrides(self) -> Settings:
        """Apply runtime env overrides that do not map 1:1 to model fields."""
        if self.rate_limit_redis_url:
            self.api.rate_limit.storage_uri = self.rate_limit_redis_url
        if self.chat_memory_redis_url:
            self.memory.redis.redis_url = self.chat_memory_redis_url
        if self.langfuse_host_override:
            self.langfuse.host = self.langfuse_host_override
        if not (self.api.rate_limit.storage_uri or "").strip():
            raise ValueError(
                "RATE_LIMIT_REDIS_URL must be configured for shared API rate limiting."
            )
        if not self.memory.redis.redis_url.strip():
            raise ValueError("CHAT_MEMORY_REDIS_URL must be configured for Redis chat memory.")
        return self


if TYPE_CHECKING:

    def _build_settings() -> Settings: ...

else:

    def _build_settings() -> Settings:
        """Build settings without altering runtime behavior in type-checking mode."""
        return Settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return _build_settings()
