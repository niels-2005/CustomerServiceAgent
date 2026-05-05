from __future__ import annotations

from tests.evals.config import load_eval_config
from tests.evals.deepeval_runner import build_agent_metrics


def test_build_agent_metrics_skips_tool_correctness_without_explicit_tool_contract() -> None:
    config = load_eval_config()

    metrics = build_agent_metrics(
        config,
        include_contextual_relevancy=True,
        has_explicit_tool_contract=False,
        has_observed_tool_calls=False,
        openai_api_key="test-key",
    )

    tool_correctness = next(metric for metric in metrics if metric.score_name == "tool_correctness")
    argument_correctness = next(
        metric for metric in metrics if metric.score_name == "argument_correctness"
    )

    assert tool_correctness.skip is True
    assert argument_correctness.skip is True


def test_build_agent_metrics_keeps_tool_correctness_for_explicit_empty_contract() -> None:
    config = load_eval_config()

    metrics = build_agent_metrics(
        config,
        include_contextual_relevancy=True,
        has_explicit_tool_contract=True,
        has_observed_tool_calls=False,
        openai_api_key="test-key",
    )

    tool_correctness = next(metric for metric in metrics if metric.score_name == "tool_correctness")
    argument_correctness = next(
        metric for metric in metrics if metric.score_name == "argument_correctness"
    )

    assert tool_correctness.skip is False
    assert argument_correctness.skip is True
