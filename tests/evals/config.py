"""Configuration loader for DeepEval-based end-to-end evaluations."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class JudgeConfig(BaseModel):
    """LLM configuration used by DeepEval judge-backed metrics."""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0)


class MetricConfig(BaseModel):
    """Thresholds and execution flags for one DeepEval metric."""

    threshold: float = Field(ge=0.0, le=1.0)
    async_mode: bool = True
    include_reason: bool = True
    strict_mode: bool = False
    verbose_mode: bool = False


class ToolCorrectnessConfig(MetricConfig):
    """Additional controls for deterministic tool correctness checks."""

    should_exact_match: bool = True
    should_consider_ordering: bool = True


class ContextualRelevancyConfig(MetricConfig):
    """Config for contextual relevancy, including skip policy."""

    skip_if_no_retrieval_context: bool = True


class MetricsConfig(BaseModel):
    """Metric-specific configuration for the eval suite."""

    exact_match: MetricConfig
    answer_relevancy: MetricConfig
    contextual_relevancy: ContextualRelevancyConfig
    tool_correctness: ToolCorrectnessConfig
    argument_correctness: MetricConfig


class LangfuseEvalConfig(BaseModel):
    """Langfuse score publishing conventions for evaluation runs."""

    score_prefix: str = Field(min_length=1)
    release_prefix: str = Field(min_length=1)
    fail_on_score_error: bool = True


class EvalConfig(BaseModel):
    """Top-level configuration for the DeepEval test harness."""

    judge: JudgeConfig
    metrics: MetricsConfig
    langfuse: LangfuseEvalConfig


CONFIG_PATH = Path(__file__).resolve().parent / "config" / "deepeval.yaml"


def load_eval_config(path: Path = CONFIG_PATH) -> EvalConfig:
    """Load the dedicated DeepEval configuration from YAML."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return EvalConfig.model_validate(payload)
