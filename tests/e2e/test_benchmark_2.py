from __future__ import annotations

import json
import time
import warnings
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError

from customer_bot.agent.tooling import FAQ_TOOL_NAME, PRODUCT_TOOL_NAME
from customer_bot.api.main import create_app
from customer_bot.config import Settings
from tests.e2e._benchmark_helpers import (
    create_langfuse_client,
    format_currency,
    format_seconds,
    ms_to_seconds,
    percentile,
    prepare_report_directories,
    publish_latest_report,
    render_markdown_table,
    resolve_runtime_session_id,
)
from tests.e2e.benchmark_2_evaluators import Benchmark2Evaluators, JudgeEvaluation

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "datasets" / "benchmark" / "benchmark_2_agent_quality_llm_judge.json"
BENCHMARK_NAME = "benchmark_2_agent_quality_llm_judge"
ARTIFACTS_ROOT = REPO_ROOT / "benchmarks" / BENCHMARK_NAME
OBSERVATION_TIMEOUT_SECONDS = 30.0
OBSERVATION_POLL_INTERVAL_SECONDS = 2.0
SUPPORTED_BENCHMARK_TOOL_NAMES = {FAQ_TOOL_NAME, PRODUCT_TOOL_NAME}


class CaseInput(BaseModel):
    """One benchmark request payload."""

    user_message: str = Field(min_length=1)
    session_id: str | None = None


class ExpectedToolCall(BaseModel):
    """Expected tool usage for one benchmark case."""

    tool_name: str = Field(min_length=1)
    query_topic: str = Field(min_length=1)


class ExpectedOutput(BaseModel):
    """Expected public contract and qualitative evidence for one case."""

    status: str
    handoff_required: bool
    guardrail_reason: str | None
    retry_used: bool
    required_facts: list[str]
    forbidden_facts: list[str]
    expected_tool_calls: list[ExpectedToolCall]


class BenchmarkCase(BaseModel):
    """Validated benchmark case loaded from the local JSON dataset."""

    case_id: str = Field(min_length=1)
    input: CaseInput
    expected_output: ExpectedOutput


class BenchmarkDataset(BaseModel):
    """Top-level benchmark dataset document."""

    cases: list[BenchmarkCase]


@dataclass(slots=True)
class TraceSnapshot:
    """Normalized Langfuse trace data needed for agent-quality evaluation."""

    total_cost: float | None
    tool_trajectory: list[str]
    tool_queries: list[str]
    tool_calls: list[dict[str, str]]
    tool_error: bool
    no_match: bool


@dataclass(slots=True)
class CaseOutcome:
    """Per-case report entry for Benchmark 2."""

    case_id: str
    user_message: str
    session_id_template: str | None
    session_id_runtime: str | None
    expected_status: str
    actual_status: str | None
    expected_handoff_required: bool
    actual_handoff_required: bool | None
    expected_guardrail_reason: str | None
    actual_guardrail_reason: str | None
    expected_retry_used: bool
    actual_retry_used: bool | None
    answer: str | None
    trace_id: str | None
    latency_ms: float | None
    total_cost: float | None
    http_status_code: int | None
    tool_trajectory: list[str]
    tool_queries: list[str]
    tool_calls: list[dict[str, str]]
    tool_error: bool
    no_match: bool
    final_answer_score: float | None
    final_answer_passed: bool
    final_answer_reasoning: str | None
    trajectory_score: float | None
    trajectory_passed: bool
    trajectory_reasoning: str | None
    query_quality_score: float | None
    query_quality_passed: bool
    query_quality_reasoning: str | None
    contract_passed: bool
    passed: bool
    failure_reason: str | None
    response_payload: dict[str, Any] | None


def _load_dataset(path: Path) -> BenchmarkDataset:
    """Load and validate the local benchmark JSON."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    normalized = raw if isinstance(raw, dict) else {"cases": raw}
    try:
        dataset = BenchmarkDataset.model_validate(normalized)
    except ValidationError as exc:
        raise ValueError(f"Benchmark JSON is invalid: {exc}") from exc
    if not dataset.cases:
        raise ValueError("Benchmark JSON has no cases.")
    return dataset


def _build_benchmark_settings() -> Settings:
    """Tune runtime settings for answered-path agent-quality benchmarking."""

    settings = Settings()
    settings.api.rate_limit.default_limit = "1000/minute"
    settings.api.rate_limit.chat_limit = "1000/minute"
    settings.memory.redis.key_prefix = "customer-bot:e2e-benchmark-llm-judge"
    settings.memory.redis.ttl_seconds = 300
    settings.langfuse.fail_fast = True
    return settings


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return count / total


def _extract_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _stringify_tool_input(value: Any) -> str:
    parsed = _extract_json(value)
    if isinstance(parsed, dict):
        for key in ("question", "query", "user_message"):
            candidate = parsed.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    if isinstance(parsed, list):
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    if parsed is None:
        return ""
    return str(parsed)


def _get_attr(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _extract_trace_snapshot(langfuse_client: Any, trace_id: str) -> TraceSnapshot:
    """Poll Langfuse until the application trace and tool observations are available."""

    deadline = time.monotonic() + OBSERVATION_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            trace = langfuse_client.api.trace.get(trace_id)
            observations = langfuse_client.api.legacy.observations_v1.get_many(
                trace_id=trace_id,
                limit=100,
            )
            tool_observations = []
            no_match = False
            tool_error = False
            for observation in observations.data:
                observation_type = str(_get_attr(observation, "type") or "").lower()
                metadata = _get_attr(observation, "metadata") or {}
                level = str(_get_attr(observation, "level") or "").upper()
                if isinstance(metadata, dict) and metadata.get("no_match") is True:
                    no_match = True
                if (
                    observation_type == "tool"
                    and _get_attr(observation, "name") in SUPPORTED_BENCHMARK_TOOL_NAMES
                ):
                    tool_observations.append(observation)
                    if level == "ERROR":
                        tool_error = True

            if tool_observations:
                tool_trajectory: list[str] = []
                tool_queries: list[str] = []
                tool_calls: list[dict[str, str]] = []
                for observation in tool_observations:
                    tool_name = str(_get_attr(observation, "name") or "").strip()
                    tool_query = _stringify_tool_input(_get_attr(observation, "input"))
                    tool_trajectory.append(tool_name)
                    tool_queries.append(tool_query)
                    tool_calls.append({"tool_name": tool_name, "tool_query": tool_query})
                total_cost = _get_attr(trace, "total_cost", "totalCost")
                return TraceSnapshot(
                    total_cost=float(total_cost) if total_cost is not None else None,
                    tool_trajectory=tool_trajectory,
                    tool_queries=tool_queries,
                    tool_calls=tool_calls,
                    tool_error=tool_error,
                    no_match=no_match,
                )
        except Exception as exc:
            last_error = exc
        time.sleep(OBSERVATION_POLL_INTERVAL_SECONDS)

    detail = f"{type(last_error).__name__}: {last_error}" if last_error is not None else "timeout"
    raise RuntimeError(
        "Langfuse trace observations were not available for benchmark evaluation "
        f"within {OBSERVATION_TIMEOUT_SECONDS:.0f}s ({detail})."
    )


def _flush_app_langfuse_client(client: TestClient) -> None:
    langfuse_client = getattr(client.app.state, "langfuse_client", None)
    if langfuse_client is None:
        return
    flush = getattr(langfuse_client, "flush", None)
    if callable(flush):
        flush()


def _collect_case_outcome(
    client: TestClient,
    langfuse_client: Any,
    evaluators: Benchmark2Evaluators,
    case: BenchmarkCase,
    *,
    runtime_session_id: str | None,
) -> CaseOutcome:
    payload: dict[str, Any] = {"user_message": case.input.user_message}
    if runtime_session_id is not None:
        payload["session_id"] = runtime_session_id

    started_at = perf_counter()
    response = client.post("/chat", json=payload)
    latency_ms = round((perf_counter() - started_at) * 1000, 3)

    response_payload: dict[str, Any] | None = None
    try:
        response_payload = response.json()
    except Exception:
        response_payload = None

    answer = None
    trace_id = None
    actual_status = None
    actual_guardrail_reason = None
    actual_handoff_required = None
    actual_retry_used = None
    total_cost = None
    tool_trajectory: list[str] = []
    tool_queries: list[str] = []
    tool_calls: list[dict[str, str]] = []
    tool_error = False
    no_match = False
    final_answer_result: JudgeEvaluation | None = None
    trajectory_result: JudgeEvaluation | None = None
    query_quality_result: JudgeEvaluation | None = None
    contract_passed = False
    failure_reasons: list[str] = []

    if response.status_code != 200:
        failure_reasons.append(
            f"unexpected http status: expected=200 actual={response.status_code}"
        )
    elif response_payload is None:
        failure_reasons.append("response body is not valid JSON")
    else:
        meta = response_payload.get("meta") or {}
        answer = response_payload.get("answer")
        trace_id = response_payload.get("trace_id")
        actual_status = meta.get("status")
        actual_guardrail_reason = meta.get("guardrail_reason")
        actual_handoff_required = response_payload.get("handoff_required")
        actual_retry_used = meta.get("retry_used")

        if actual_status != case.expected_output.status:
            failure_reasons.append(
                f"status mismatch: expected={case.expected_output.status} actual={actual_status}"
            )
        if actual_guardrail_reason != case.expected_output.guardrail_reason:
            failure_reasons.append(
                "guardrail_reason mismatch: "
                f"expected={case.expected_output.guardrail_reason} actual={actual_guardrail_reason}"
            )
        if actual_handoff_required != case.expected_output.handoff_required:
            failure_reasons.append(
                "handoff_required mismatch: "
                f"expected={case.expected_output.handoff_required} actual={actual_handoff_required}"
            )
        if actual_retry_used != case.expected_output.retry_used:
            failure_reasons.append(
                "retry_used mismatch: "
                f"expected={case.expected_output.retry_used} actual={actual_retry_used}"
            )

        contract_passed = not failure_reasons

        if trace_id is None:
            failure_reasons.append("trace_id missing from /chat response")
        else:
            _flush_app_langfuse_client(client)
            try:
                trace_snapshot = _extract_trace_snapshot(langfuse_client, trace_id)
            except Exception as exc:
                failure_reasons.append(
                    f"langfuse trace extraction failed: {type(exc).__name__}: {exc}"
                )
            else:
                total_cost = trace_snapshot.total_cost
                tool_trajectory = trace_snapshot.tool_trajectory
                tool_queries = trace_snapshot.tool_queries
                tool_calls = trace_snapshot.tool_calls
                tool_error = trace_snapshot.tool_error
                no_match = trace_snapshot.no_match
                if answer is None:
                    failure_reasons.append("answer missing from /chat response")
                else:
                    try:
                        final_answer_result = evaluators.evaluate_final_answer(
                            user_message=case.input.user_message,
                            answer=answer,
                            required_facts=case.expected_output.required_facts,
                            forbidden_facts=case.expected_output.forbidden_facts,
                        )
                        trajectory_result = evaluators.evaluate_trajectory(
                            expected_tool_calls=[
                                tool_call.model_dump(mode="json")
                                for tool_call in case.expected_output.expected_tool_calls
                            ],
                            actual_tool_trajectory=tool_trajectory,
                        )
                        query_quality_result = evaluators.evaluate_query_quality(
                            expected_tool_calls=[
                                tool_call.model_dump(mode="json")
                                for tool_call in case.expected_output.expected_tool_calls
                            ],
                            actual_tool_calls=tool_calls,
                        )
                    except Exception as exc:
                        failure_reasons.append(
                            f"judge evaluation failed: {type(exc).__name__}: {exc}"
                        )
                    else:
                        if not final_answer_result.passed:
                            failure_reasons.append(
                                f"final_answer evaluator failed: {final_answer_result.reasoning}"
                            )
                        if not trajectory_result.passed:
                            failure_reasons.append(trajectory_result.reasoning)
                        if not query_quality_result.passed:
                            failure_reasons.append(
                                f"query_quality evaluator failed: {query_quality_result.reasoning}"
                            )

    passed = (
        contract_passed
        and final_answer_result is not None
        and trajectory_result is not None
        and query_quality_result is not None
        and final_answer_result.passed
        and trajectory_result.passed
        and query_quality_result.passed
    )

    return CaseOutcome(
        case_id=case.case_id,
        user_message=case.input.user_message,
        session_id_template=case.input.session_id,
        session_id_runtime=runtime_session_id,
        expected_status=case.expected_output.status,
        actual_status=actual_status,
        expected_handoff_required=case.expected_output.handoff_required,
        actual_handoff_required=actual_handoff_required,
        expected_guardrail_reason=case.expected_output.guardrail_reason,
        actual_guardrail_reason=actual_guardrail_reason,
        expected_retry_used=case.expected_output.retry_used,
        actual_retry_used=actual_retry_used,
        answer=answer,
        trace_id=trace_id,
        latency_ms=latency_ms,
        total_cost=total_cost,
        http_status_code=response.status_code,
        tool_trajectory=tool_trajectory,
        tool_queries=tool_queries,
        tool_calls=tool_calls,
        tool_error=tool_error,
        no_match=no_match,
        final_answer_score=final_answer_result.score if final_answer_result else None,
        final_answer_passed=final_answer_result.passed if final_answer_result else False,
        final_answer_reasoning=final_answer_result.reasoning if final_answer_result else None,
        trajectory_score=trajectory_result.score if trajectory_result else None,
        trajectory_passed=trajectory_result.passed if trajectory_result else False,
        trajectory_reasoning=trajectory_result.reasoning if trajectory_result else None,
        query_quality_score=query_quality_result.score if query_quality_result else None,
        query_quality_passed=query_quality_result.passed if query_quality_result else False,
        query_quality_reasoning=query_quality_result.reasoning if query_quality_result else None,
        contract_passed=contract_passed,
        passed=passed,
        failure_reason="; ".join(failure_reasons) or None,
        response_payload=response_payload,
    )


def _count_expected_status(cases: list[BenchmarkCase], status: str) -> int:
    return sum(1 for case in cases if case.expected_output.status == status)


def _count_actual_status(outcomes: list[CaseOutcome], status: str) -> int:
    return sum(1 for outcome in outcomes if outcome.actual_status == status)


def _count_expected_bool(cases: list[BenchmarkCase], field_name: str) -> int:
    return sum(1 for case in cases if getattr(case.expected_output, field_name) is True)


def _count_actual_bool(outcomes: list[CaseOutcome], field_name: str) -> int:
    return sum(1 for outcome in outcomes if getattr(outcome, field_name) is True)


def _count_expected_guardrail(cases: list[BenchmarkCase]) -> int:
    return sum(1 for case in cases if case.expected_output.guardrail_reason is not None)


def _count_actual_guardrail(outcomes: list[CaseOutcome], reason: str | None = None) -> int:
    if reason is None:
        return sum(1 for outcome in outcomes if outcome.actual_guardrail_reason is not None)
    return sum(1 for outcome in outcomes if outcome.actual_guardrail_reason == reason)


def _avg_score(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 4)


def _write_report(
    report_dir: Path,
    run_slug: str,
    dataset: BenchmarkDataset,
    outcomes: list[CaseOutcome],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=False)

    total_cases = len(dataset.cases)
    passed_cases = sum(1 for outcome in outcomes if outcome.passed)
    failed_cases = total_cases - passed_cases
    error_count = sum(1 for outcome in outcomes if outcome.http_status_code != 200)
    latencies = [outcome.latency_ms for outcome in outcomes if outcome.latency_ms is not None]
    avg_latency_ms = round(sum(latencies) / len(latencies), 3) if latencies else None
    p50_latency_ms = percentile(latencies, 50)
    p90_latency_ms = percentile(latencies, 90)
    costs = [outcome.total_cost for outcome in outcomes if outcome.total_cost is not None]
    avg_price = round(sum(costs) / len(costs), 6) if costs else None
    total_costs = round(sum(costs), 6) if costs else None
    price_enrichment_status = "resolved" if costs else "resolved_no_costs"

    answered_count_actual = _count_actual_status(outcomes, "answered")
    answered_count_expected = _count_expected_status(dataset.cases, "answered")
    retry_used_count_actual = _count_actual_bool(outcomes, "actual_retry_used")
    retry_used_count_expected = _count_expected_bool(dataset.cases, "retry_used")
    handoff_count_actual = _count_actual_bool(outcomes, "actual_handoff_required")
    handoff_count_expected = _count_expected_bool(dataset.cases, "handoff_required")
    unexpected_guardrail_count_actual = _count_actual_guardrail(outcomes)
    unexpected_guardrail_count_expected = _count_expected_guardrail(dataset.cases)
    fallback_count_actual = _count_actual_status(outcomes, "fallback")
    grounding_count_actual = _count_actual_guardrail(outcomes, "grounding")
    bias_count_actual = _count_actual_guardrail(outcomes, "bias")
    guardrail_error_count_actual = _count_actual_guardrail(outcomes, "guardrail_error")

    final_answer_pass_rate = _rate(
        sum(1 for outcome in outcomes if outcome.final_answer_passed),
        total_cases,
    )
    trajectory_pass_rate = _rate(
        sum(1 for outcome in outcomes if outcome.trajectory_passed), total_cases
    )
    query_quality_pass_rate = _rate(
        sum(1 for outcome in outcomes if outcome.query_quality_passed),
        total_cases,
    )

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark_name": BENCHMARK_NAME,
        "run_slug": run_slug,
        "dataset_path": str(DATASET_PATH.relative_to(REPO_ROOT)),
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": round(_rate(passed_cases, total_cases), 4),
        "error_count": error_count,
        "avg_latency_ms": avg_latency_ms,
        "avg_latency_s": ms_to_seconds(avg_latency_ms),
        "p50_latency_ms": p50_latency_ms,
        "p50_latency_s": ms_to_seconds(p50_latency_ms),
        "p90_latency_ms": p90_latency_ms,
        "p90_latency_s": ms_to_seconds(p90_latency_ms),
        "avg_price": avg_price,
        "total_costs": total_costs,
        "price_enrichment_status": price_enrichment_status,
        "answered_count_actual": answered_count_actual,
        "answered_count_expected": answered_count_expected,
        "answered_rate_actual": round(_rate(answered_count_actual, total_cases), 4),
        "answered_rate_expected": round(_rate(answered_count_expected, total_cases), 4),
        "retry_used_count_actual": retry_used_count_actual,
        "retry_used_count_expected": retry_used_count_expected,
        "retry_used_rate_actual": round(_rate(retry_used_count_actual, total_cases), 4),
        "retry_used_rate_expected": round(_rate(retry_used_count_expected, total_cases), 4),
        "handoff_count_actual": handoff_count_actual,
        "handoff_count_expected": handoff_count_expected,
        "handoff_rate_actual": round(_rate(handoff_count_actual, total_cases), 4),
        "handoff_rate_expected": round(_rate(handoff_count_expected, total_cases), 4),
        "unexpected_guardrail_count_actual": unexpected_guardrail_count_actual,
        "unexpected_guardrail_count_expected": unexpected_guardrail_count_expected,
        "unexpected_guardrail_rate_actual": round(
            _rate(unexpected_guardrail_count_actual, total_cases), 4
        ),
        "unexpected_guardrail_rate_expected": round(
            _rate(unexpected_guardrail_count_expected, total_cases), 4
        ),
        "fallback_rate_actual": round(_rate(fallback_count_actual, total_cases), 4),
        "grounding_rate_actual": round(_rate(grounding_count_actual, total_cases), 4),
        "bias_rate_actual": round(_rate(bias_count_actual, total_cases), 4),
        "guardrail_error_rate_actual": round(_rate(guardrail_error_count_actual, total_cases), 4),
        "fallback_rate_expected": 0.0,
        "grounding_rate_expected": 0.0,
        "bias_rate_expected": 0.0,
        "guardrail_error_rate_expected": 0.0,
        "final_answer_avg_score": _avg_score([outcome.final_answer_score for outcome in outcomes]),
        "final_answer_pass_rate": round(final_answer_pass_rate, 4),
        "trajectory_avg_score": _avg_score([outcome.trajectory_score for outcome in outcomes]),
        "trajectory_pass_rate": round(trajectory_pass_rate, 4),
        "query_quality_avg_score": _avg_score(
            [outcome.query_quality_score for outcome in outcomes]
        ),
        "query_quality_pass_rate": round(query_quality_pass_rate, 4),
        "tool_usage_rate": round(
            _rate(sum(1 for outcome in outcomes if outcome.tool_trajectory), total_cases),
            4,
        ),
        "tool_error_rate": round(
            _rate(sum(1 for outcome in outcomes if outcome.tool_error), total_cases),
            4,
        ),
        "no_match_rate": round(
            _rate(sum(1 for outcome in outcomes if outcome.no_match), total_cases),
            4,
        ),
    }

    report_payload = {
        "summary": summary,
        "cases": [asdict(outcome) for outcome in outcomes],
    }
    summary_json = report_dir / "summary.json"
    summary_json.write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = ["# Benchmark 2 Summary", "", "## Overview", ""]
    lines.extend(
        render_markdown_table(
            ["Field", "Value"],
            [
                ["Benchmark", f"`{summary['benchmark_name']}`"],
                ["Dataset", f"`{summary['dataset_path']}`"],
                ["Run Slug", f"`{summary['run_slug']}`"],
                ["Total Cases", str(total_cases)],
                ["Passed Cases", str(passed_cases)],
                ["Failed Cases", str(failed_cases)],
                ["Pass Rate", f"{summary['pass_rate']:.2%}"],
                ["Error Count", str(error_count)],
            ],
        )
    )
    lines.extend(["", "## Performance", ""])
    lines.extend(
        render_markdown_table(
            ["Metric", "Value"],
            [
                ["Avg Latency", format_seconds(avg_latency_ms)],
                ["P50 Latency", format_seconds(p50_latency_ms)],
                ["P90 Latency", format_seconds(p90_latency_ms)],
            ],
        )
    )
    lines.extend(["", "## Cost", ""])
    lines.extend(
        render_markdown_table(
            ["Metric", "Value"],
            [
                ["Avg Price", format_currency(summary["avg_price"])],
                ["Total Costs", format_currency(summary["total_costs"])],
                ["Price Enrichment", summary["price_enrichment_status"]],
            ],
        )
    )
    lines.extend(["", "## Contract Metrics", ""])
    lines.extend(
        render_markdown_table(
            ["Metric", "Actual Count", "Expected Count", "Actual Rate", "Expected Rate"],
            [
                [
                    "Answered",
                    str(summary["answered_count_actual"]),
                    str(summary["answered_count_expected"]),
                    f"{summary['answered_rate_actual']:.2%}",
                    f"{summary['answered_rate_expected']:.2%}",
                ],
                [
                    "Retry Used",
                    str(summary["retry_used_count_actual"]),
                    str(summary["retry_used_count_expected"]),
                    f"{summary['retry_used_rate_actual']:.2%}",
                    f"{summary['retry_used_rate_expected']:.2%}",
                ],
                [
                    "Handoff",
                    str(summary["handoff_count_actual"]),
                    str(summary["handoff_count_expected"]),
                    f"{summary['handoff_rate_actual']:.2%}",
                    f"{summary['handoff_rate_expected']:.2%}",
                ],
                [
                    "Unexpected Guardrail",
                    str(summary["unexpected_guardrail_count_actual"]),
                    str(summary["unexpected_guardrail_count_expected"]),
                    f"{summary['unexpected_guardrail_rate_actual']:.2%}",
                    f"{summary['unexpected_guardrail_rate_expected']:.2%}",
                ],
            ],
        )
    )
    lines.extend(["", "## Agent Quality Metrics", ""])
    lines.extend(
        render_markdown_table(
            ["Metric", "Value"],
            [
                ["Final Answer Avg Score", str(summary["final_answer_avg_score"])],
                ["Final Answer Pass Rate", f"{summary['final_answer_pass_rate']:.2%}"],
                ["Trajectory Avg Score", str(summary["trajectory_avg_score"])],
                ["Trajectory Pass Rate", f"{summary['trajectory_pass_rate']:.2%}"],
                ["Query Quality Avg Score", str(summary["query_quality_avg_score"])],
                ["Query Quality Pass Rate", f"{summary['query_quality_pass_rate']:.2%}"],
                ["Tool Usage Rate", f"{summary['tool_usage_rate']:.2%}"],
                ["Tool Error Rate", f"{summary['tool_error_rate']:.2%}"],
                ["No Match Rate", f"{summary['no_match_rate']:.2%}"],
            ],
        )
    )
    lines.extend(["", "## Output Guardrail Signals", ""])
    lines.extend(
        render_markdown_table(
            ["Metric", "Actual Rate", "Expected Rate"],
            [
                [
                    "Fallback",
                    f"{summary['fallback_rate_actual']:.2%}",
                    f"{summary['fallback_rate_expected']:.2%}",
                ],
                [
                    "Grounding",
                    f"{summary['grounding_rate_actual']:.2%}",
                    f"{summary['grounding_rate_expected']:.2%}",
                ],
                [
                    "Bias",
                    f"{summary['bias_rate_actual']:.2%}",
                    f"{summary['bias_rate_expected']:.2%}",
                ],
                [
                    "Guardrail Error",
                    f"{summary['guardrail_error_rate_actual']:.2%}",
                    f"{summary['guardrail_error_rate_expected']:.2%}",
                ],
            ],
        )
    )
    failed_outcomes = [outcome for outcome in outcomes if not outcome.passed]
    if failed_outcomes:
        lines.extend(["", "## Failed Cases", ""])
        lines.extend(
            render_markdown_table(
                [
                    "Case ID",
                    "Failure Reason",
                    "Trace ID",
                    "Trajectory Reasoning",
                    "Answer Reasoning",
                    "Query Reasoning",
                ],
                [
                    [
                        outcome.case_id,
                        outcome.failure_reason or "",
                        outcome.trace_id or "",
                        outcome.trajectory_reasoning or "",
                        outcome.final_answer_reasoning or "",
                        outcome.query_quality_reasoning or "",
                    ]
                    for outcome in failed_outcomes
                ],
            )
        )

    (report_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_json


@pytest.mark.e2e
@pytest.mark.eval_llm_judge
@pytest.mark.network
def test_benchmark_2_agent_quality(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the answered-path LLM-as-a-judge benchmark and emit a local report."""

    if not DATASET_PATH.exists():
        pytest.fail(f"Benchmark dataset not found: {DATASET_PATH}")

    dataset = _load_dataset(DATASET_PATH)
    run_slug, report_dir, latest_dir = prepare_report_directories(ARTIFACTS_ROOT)
    outcomes: list[CaseOutcome] = []
    startup_error: str | None = None

    settings = _build_benchmark_settings()
    langfuse_client = create_langfuse_client(settings)
    if langfuse_client is None:
        pytest.fail("Benchmark 2 requires Langfuse credentials for trace-based evaluation.")

    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)

    try:
        evaluators = Benchmark2Evaluators(settings)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            app = create_app(enable_observability=True, run_startup_checks=True)
            with TestClient(app) as client:
                for case in dataset.cases:
                    runtime_session_id = resolve_runtime_session_id(run_slug, case.input.session_id)
                    outcomes.append(
                        _collect_case_outcome(
                            client,
                            langfuse_client,
                            evaluators,
                            case,
                            runtime_session_id=runtime_session_id,
                        )
                    )
    except Exception as exc:
        startup_error = f"{type(exc).__name__}: {exc}"

    if startup_error is not None:
        report_dir.mkdir(parents=True, exist_ok=False)
        summary_json = report_dir / "summary.json"
        summary_json.write_text(
            json.dumps(
                {
                    "summary": {
                        "generated_at": datetime.now(UTC).isoformat(),
                        "benchmark_name": BENCHMARK_NAME,
                        "run_slug": run_slug,
                        "dataset_path": str(DATASET_PATH.relative_to(REPO_ROOT)),
                        "startup_error": startup_error,
                    },
                    "cases": [],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (report_dir / "summary.md").write_text(
            "# Benchmark 2 Summary\n\n"
            f"- Benchmark: `{BENCHMARK_NAME}`\n"
            f"- Dataset: `{DATASET_PATH.relative_to(REPO_ROOT)}`\n"
            f"- Run Slug: `{run_slug}`\n"
            f"- Startup Error: {startup_error}\n",
            encoding="utf-8",
        )
        publish_latest_report(report_dir, latest_dir)
        pytest.fail(f"Benchmark startup failed. See report: {summary_json}")

    summary_json = _write_report(report_dir, run_slug, dataset, outcomes)
    publish_latest_report(report_dir, latest_dir)
    summary = json.loads(summary_json.read_text(encoding="utf-8"))["summary"]

    contract_failures = [outcome for outcome in outcomes if not outcome.contract_passed]
    quality_case_failures = [
        outcome for outcome in outcomes if outcome.contract_passed and not outcome.passed
    ]
    threshold_failures: list[str] = []
    if summary["final_answer_pass_rate"] < evaluators.final_answer_pass_rate_threshold:
        threshold_failures.append(
            "final_answer_pass_rate below threshold: "
            f"{summary['final_answer_pass_rate']:.2%} < "
            f"{evaluators.final_answer_pass_rate_threshold:.0%}"
        )
    if summary["trajectory_pass_rate"] < evaluators.trajectory_pass_rate_threshold:
        threshold_failures.append(
            "trajectory_pass_rate below threshold: "
            f"{summary['trajectory_pass_rate']:.2%} < "
            f"{evaluators.trajectory_pass_rate_threshold:.0%}"
        )
    if summary["query_quality_pass_rate"] < evaluators.query_quality_pass_rate_threshold:
        threshold_failures.append(
            "query_quality_pass_rate below threshold: "
            f"{summary['query_quality_pass_rate']:.2%} < "
            f"{evaluators.query_quality_pass_rate_threshold:.0%}"
        )
    for metric_name in (
        "fallback_rate_actual",
        "grounding_rate_actual",
        "bias_rate_actual",
        "guardrail_error_rate_actual",
    ):
        if summary[metric_name] > 0:
            threshold_failures.append(
                f"{metric_name} should remain at 0 but was {summary[metric_name]:.2%}"
            )

    if contract_failures or quality_case_failures or threshold_failures:
        failure_summary = []
        if contract_failures:
            failure_summary.append(f"{len(contract_failures)} contract case(s)")
        if quality_case_failures:
            failure_summary.append(f"{len(quality_case_failures)} quality case(s)")
        if threshold_failures:
            failure_summary.append("; ".join(threshold_failures))
        pytest.fail(
            "Benchmark 2 failed: " + " | ".join(failure_summary) + f". See report: {summary_json}"
        )
