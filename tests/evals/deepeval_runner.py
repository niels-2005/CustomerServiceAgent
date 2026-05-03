"""DeepEval metric construction and assertion helpers."""

from __future__ import annotations

from dataclasses import dataclass

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ArgumentCorrectnessMetric,
    ContextualRelevancyMetric,
    ExactMatchMetric,
    ToolCorrectnessMetric,
)
from deepeval.models import GPTModel
from deepeval.test_case import LLMTestCase

from tests.evals.config import EvalConfig
from tests.evals.langfuse_bridge import MetricOutcome


@dataclass(slots=True)
class MetricDefinition:
    """One instantiated DeepEval metric plus its assertion threshold."""

    score_name: str
    threshold: float
    metric: object
    skip: bool = False
    skip_reason: str | None = None


def build_guardrail_metrics(config: EvalConfig) -> list[MetricDefinition]:
    """Build the deterministic metric set for input-guardrail cases."""

    metric_config = config.metrics.exact_match
    return [
        MetricDefinition(
            score_name="exact_match",
            threshold=metric_config.threshold,
            metric=ExactMatchMetric(
                threshold=metric_config.threshold,
                verbose_mode=metric_config.verbose_mode,
            ),
        )
    ]


def build_agent_metrics(
    config: EvalConfig,
    *,
    include_contextual_relevancy: bool,
    openai_api_key: str,
) -> list[MetricDefinition]:
    """Build the DeepEval metric set for answered-path agent cases."""

    judge_model = _build_judge_model(config, openai_api_key=openai_api_key)
    definitions = [
        MetricDefinition(
            score_name="answer_relevancy",
            threshold=config.metrics.answer_relevancy.threshold,
            metric=AnswerRelevancyMetric(
                threshold=config.metrics.answer_relevancy.threshold,
                model=judge_model,
                include_reason=config.metrics.answer_relevancy.include_reason,
                async_mode=config.metrics.answer_relevancy.async_mode,
                strict_mode=config.metrics.answer_relevancy.strict_mode,
                verbose_mode=config.metrics.answer_relevancy.verbose_mode,
            ),
        ),
        MetricDefinition(
            score_name="tool_correctness",
            threshold=config.metrics.tool_correctness.threshold,
            metric=ToolCorrectnessMetric(
                threshold=config.metrics.tool_correctness.threshold,
                model=judge_model,
                include_reason=config.metrics.tool_correctness.include_reason,
                async_mode=config.metrics.tool_correctness.async_mode,
                strict_mode=config.metrics.tool_correctness.strict_mode,
                verbose_mode=config.metrics.tool_correctness.verbose_mode,
                should_exact_match=config.metrics.tool_correctness.should_exact_match,
                should_consider_ordering=config.metrics.tool_correctness.should_consider_ordering,
            ),
        ),
        MetricDefinition(
            score_name="argument_correctness",
            threshold=config.metrics.argument_correctness.threshold,
            metric=ArgumentCorrectnessMetric(
                threshold=config.metrics.argument_correctness.threshold,
                model=judge_model,
                include_reason=config.metrics.argument_correctness.include_reason,
                async_mode=config.metrics.argument_correctness.async_mode,
                strict_mode=config.metrics.argument_correctness.strict_mode,
                verbose_mode=config.metrics.argument_correctness.verbose_mode,
            ),
        ),
    ]
    if include_contextual_relevancy:
        definitions.insert(
            1,
            MetricDefinition(
                score_name="contextual_relevancy",
                threshold=config.metrics.contextual_relevancy.threshold,
                metric=ContextualRelevancyMetric(
                    threshold=config.metrics.contextual_relevancy.threshold,
                    model=judge_model,
                    include_reason=config.metrics.contextual_relevancy.include_reason,
                    async_mode=config.metrics.contextual_relevancy.async_mode,
                    strict_mode=config.metrics.contextual_relevancy.strict_mode,
                    verbose_mode=config.metrics.contextual_relevancy.verbose_mode,
                ),
            ),
        )
    else:
        definitions.insert(
            1,
            MetricDefinition(
                score_name="contextual_relevancy",
                threshold=config.metrics.contextual_relevancy.threshold,
                metric=ContextualRelevancyMetric(
                    threshold=config.metrics.contextual_relevancy.threshold,
                    model=judge_model,
                    include_reason=config.metrics.contextual_relevancy.include_reason,
                    async_mode=config.metrics.contextual_relevancy.async_mode,
                    strict_mode=config.metrics.contextual_relevancy.strict_mode,
                    verbose_mode=config.metrics.contextual_relevancy.verbose_mode,
                ),
                skip=config.metrics.contextual_relevancy.skip_if_no_retrieval_context,
                skip_reason=(
                    "retrieval_context is empty or only contains no-match sentinel evidence"
                ),
            ),
        )
    return definitions


def measure_metrics(
    test_case: LLMTestCase,
    metric_definitions: list[MetricDefinition],
) -> tuple[list[MetricOutcome], list[str]]:
    """Execute DeepEval metrics and return normalized outcomes plus failures."""

    outcomes: list[MetricOutcome] = []
    failures: list[str] = []
    for definition in metric_definitions:
        if definition.skip:
            continue

        metric = definition.metric
        try:
            metric.measure(test_case)
        except Exception as exc:
            failures.append(
                f"{definition.score_name} execution failed: {type(exc).__name__}: {exc}"
            )
            continue

        score = float(metric.score)
        reason = _normalize_reason(getattr(metric, "reason", None))
        passed = score >= definition.threshold
        outcomes.append(
            MetricOutcome(
                score_name=definition.score_name,
                value=score,
                threshold=definition.threshold,
                passed=passed,
                reason=reason,
            )
        )
        if not passed:
            failures.append(
                f"{definition.score_name} below threshold: "
                f"score={score:.4f} threshold={definition.threshold:.4f} reason={reason or 'n/a'}"
            )
    return outcomes, failures


def _normalize_reason(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _build_judge_model(config: EvalConfig, *, openai_api_key: str) -> GPTModel:
    provider = config.judge.provider.strip().lower()
    if provider != "openai":
        raise ValueError(f"Unsupported DeepEval judge provider: {config.judge.provider}")
    if not openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required for DeepEval judge metrics.")
    return GPTModel(model=config.judge.model, api_key=openai_api_key)
