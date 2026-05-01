from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pytest
from fastapi.testclient import TestClient

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

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    REPO_ROOT / "datasets" / "benchmark" / "benchmark_1_input_guardrails_deterministic.json"
)
BENCHMARK_NAME = "benchmark_1_input_guardrails_deterministic"
ARTIFACTS_ROOT = REPO_ROOT / "benchmarks" / BENCHMARK_NAME


@dataclass(slots=True)
class BenchmarkCase:
    """One benchmark case parsed from the JSON dataset."""

    case_id: str
    user_message: str
    session_id: str | None
    expected_guardrail_reason: str | None
    expected_status: str
    expected_handoff_required: bool


@dataclass(slots=True)
class CaseOutcome:
    """Normalized per-case result stored in the benchmark report."""

    case_id: str
    user_message: str
    session_id_template: str | None
    session_id_runtime: str | None
    expected_guardrail_reason: str | None
    actual_guardrail_reason: str | None
    expected_status: str
    actual_status: str | None
    expected_handoff_required: bool
    actual_handoff_required: bool | None
    trace_id: str | None
    latency_ms: float | None
    total_cost: float | None
    http_status_code: int | None
    passed: bool
    failure_reason: str | None
    response_payload: dict[str, Any] | None


def _load_cases(path: Path) -> list[BenchmarkCase]:
    """Read the JSON benchmark dataset in file order."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("cases")
    if not isinstance(items, list):
        raise ValueError("Benchmark JSON must contain a top-level list or a 'cases' array.")

    required_fields = {
        "case_id",
        "user_message",
        "session_id",
        "expected_guardrail_reason",
        "expected_status",
        "expected_handoff_required",
    }
    cases: list[BenchmarkCase] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each benchmark case in the JSON dataset must be an object.")
        missing = sorted(required_fields - set(item))
        if missing:
            raise ValueError(f"Benchmark JSON case is missing required fields: {missing}")
        session_id = _normalize_optional_text(item.get("session_id"))
        expected_reason = _normalize_optional_text(item.get("expected_guardrail_reason"))
        handoff = _parse_bool(item.get("expected_handoff_required"))
        user_message = item.get("user_message")
        expected_status = item.get("expected_status")
        case_id = item.get("case_id")
        if (
            not isinstance(user_message, str)
            or not isinstance(expected_status, str)
            or not isinstance(case_id, str)
        ):
            raise ValueError(
                "Benchmark JSON case_id, user_message, and expected_status must be strings."
            )
        cases.append(
            BenchmarkCase(
                case_id=case_id.strip(),
                user_message=user_message,
                session_id=session_id,
                expected_guardrail_reason=expected_reason,
                expected_status=expected_status.strip(),
                expected_handoff_required=handoff,
            )
        )
    if not cases:
        raise ValueError("Benchmark JSON has no cases.")
    return cases


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Unsupported boolean value in benchmark JSON: {value!r}")
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Unsupported boolean value in benchmark JSON: {value!r}")


def _normalize_optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    if not normalized or normalized.lower() == "null":
        return None
    return normalized


def _count_expected(cases: list[BenchmarkCase], reason: str) -> int:
    return sum(1 for case in cases if case.expected_guardrail_reason == reason)


def _count_actual(outcomes: list[CaseOutcome], reason: str) -> int:
    return sum(1 for outcome in outcomes if outcome.actual_guardrail_reason == reason)


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return count / total


def _build_benchmark_settings() -> Settings:
    """Tighten runtime settings so the benchmark only exercises input guardrails."""
    settings = Settings()
    settings.api.rate_limit.default_limit = "1000/minute"
    settings.api.rate_limit.chat_limit = "1000/minute"
    settings.memory.redis.key_prefix = "customer-bot:e2e-benchmark"
    settings.memory.redis.ttl_seconds = 300
    settings.guardrails.output.pii.enabled = False
    settings.guardrails.output.grounding.enabled = False
    settings.guardrails.output.bias.enabled = False
    settings.guardrails.global_.max_output_retries = 0
    return settings


def _enrich_costs_from_langfuse(outcomes: list[CaseOutcome], settings: Settings) -> str:
    client = create_langfuse_client(settings)
    if client is None:
        return "skipped_missing_langfuse_credentials"

    resolved_any = False
    for outcome in outcomes:
        if outcome.trace_id is None:
            continue
        try:
            trace = client.api.trace.get(outcome.trace_id)
        except Exception:
            continue

        total_cost = getattr(trace, "total_cost", None)
        if total_cost is None:
            continue

        outcome.total_cost = float(total_cost)
        resolved_any = True

    return "resolved" if resolved_any else "resolved_no_costs"


def _run_case(
    client: TestClient,
    case: BenchmarkCase,
    *,
    runtime_session_id: str | None,
) -> CaseOutcome:
    payload: dict[str, Any] = {"user_message": case.user_message}
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

    trace_id = None
    actual_status = None
    actual_guardrail_reason = None
    actual_handoff_required = None
    failure_reason = None
    passed = False

    if response.status_code != 200:
        failure_reason = f"unexpected http status: expected=200 actual={response.status_code}"
    elif response_payload is None:
        failure_reason = "response body is not valid JSON"
    else:
        meta = response_payload.get("meta") or {}
        trace_id = response_payload.get("trace_id")
        actual_status = meta.get("status")
        actual_guardrail_reason = meta.get("guardrail_reason")
        actual_handoff_required = response_payload.get("handoff_required")

        mismatches: list[str] = []
        if actual_guardrail_reason != case.expected_guardrail_reason:
            mismatches.append(
                "guardrail_reason mismatch: "
                f"expected={case.expected_guardrail_reason} actual={actual_guardrail_reason}"
            )
        if actual_status != case.expected_status:
            mismatches.append(
                f"status mismatch: expected={case.expected_status} actual={actual_status}"
            )
        if actual_handoff_required != case.expected_handoff_required:
            mismatches.append(
                "handoff_required mismatch: "
                f"expected={case.expected_handoff_required} actual={actual_handoff_required}"
            )
        passed = not mismatches
        failure_reason = "; ".join(mismatches) or None

    return CaseOutcome(
        case_id=case.case_id,
        user_message=case.user_message,
        session_id_template=case.session_id,
        session_id_runtime=runtime_session_id,
        expected_guardrail_reason=case.expected_guardrail_reason,
        actual_guardrail_reason=actual_guardrail_reason,
        expected_status=case.expected_status,
        actual_status=actual_status,
        expected_handoff_required=case.expected_handoff_required,
        actual_handoff_required=actual_handoff_required,
        trace_id=trace_id,
        latency_ms=latency_ms,
        total_cost=None,
        http_status_code=response.status_code,
        passed=passed,
        failure_reason=failure_reason,
        response_payload=response_payload,
    )


def _write_report(
    report_dir: Path,
    run_slug: str,
    cases: list[BenchmarkCase],
    outcomes: list[CaseOutcome],
    *,
    price_enrichment_status: str,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=False)

    total_cases = len(cases)
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

    expected_counts = {
        "pii": _count_expected(cases, "secret_pii"),
        "prompt_injection": _count_expected(cases, "prompt_injection"),
        "off_topic": _count_expected(cases, "off_topic"),
        "escalation": _count_expected(cases, "escalation"),
    }
    actual_counts = {
        "pii": _count_actual(outcomes, "secret_pii"),
        "prompt_injection": _count_actual(outcomes, "prompt_injection"),
        "off_topic": _count_actual(outcomes, "off_topic"),
        "escalation": _count_actual(outcomes, "escalation"),
    }

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
        "pii_count_actual": actual_counts["pii"],
        "pii_count_expected": expected_counts["pii"],
        "pii_rate_actual": round(_rate(actual_counts["pii"], total_cases), 4),
        "pii_rate_expected": round(_rate(expected_counts["pii"], total_cases), 4),
        "prompt_injection_count_actual": actual_counts["prompt_injection"],
        "prompt_injection_count_expected": expected_counts["prompt_injection"],
        "prompt_injection_rate_actual": round(
            _rate(actual_counts["prompt_injection"], total_cases), 4
        ),
        "prompt_injection_rate_expected": round(
            _rate(expected_counts["prompt_injection"], total_cases), 4
        ),
        "off_topic_count_actual": actual_counts["off_topic"],
        "off_topic_count_expected": expected_counts["off_topic"],
        "off_topic_rate_actual": round(_rate(actual_counts["off_topic"], total_cases), 4),
        "off_topic_rate_expected": round(_rate(expected_counts["off_topic"], total_cases), 4),
        "escalation_count_actual": actual_counts["escalation"],
        "escalation_count_expected": expected_counts["escalation"],
        "escalation_rate_actual": round(_rate(actual_counts["escalation"], total_cases), 4),
        "escalation_rate_expected": round(_rate(expected_counts["escalation"], total_cases), 4),
    }

    failed_outcomes = [outcome for outcome in outcomes if not outcome.passed]
    report_payload = {
        "summary": summary,
        "cases": [asdict(outcome) for outcome in outcomes],
    }
    summary_json = report_dir / "summary.json"
    summary_json.write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = ["# Benchmark 1 Summary", "", "## Overview", ""]
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
    lines.extend(["", "## Guardrail Metrics", ""])
    lines.extend(
        render_markdown_table(
            ["Metric", "Actual Count", "Expected Count", "Actual Rate", "Expected Rate"],
            [
                [
                    "PII",
                    str(summary["pii_count_actual"]),
                    str(summary["pii_count_expected"]),
                    f"{summary['pii_rate_actual']:.2%}",
                    f"{summary['pii_rate_expected']:.2%}",
                ],
                [
                    "Prompt Injection",
                    str(summary["prompt_injection_count_actual"]),
                    str(summary["prompt_injection_count_expected"]),
                    f"{summary['prompt_injection_rate_actual']:.2%}",
                    f"{summary['prompt_injection_rate_expected']:.2%}",
                ],
                [
                    "Off Topic",
                    str(summary["off_topic_count_actual"]),
                    str(summary["off_topic_count_expected"]),
                    f"{summary['off_topic_rate_actual']:.2%}",
                    f"{summary['off_topic_rate_expected']:.2%}",
                ],
                [
                    "Escalation",
                    str(summary["escalation_count_actual"]),
                    str(summary["escalation_count_expected"]),
                    f"{summary['escalation_rate_actual']:.2%}",
                    f"{summary['escalation_rate_expected']:.2%}",
                ],
            ],
        )
    )
    if failed_outcomes:
        lines.extend(["", "## Failed Cases", ""])
        lines.extend(
            render_markdown_table(
                ["Case ID", "Failure Reason", "Trace ID", "Runtime Session ID"],
                [
                    [
                        outcome.case_id,
                        outcome.failure_reason or "",
                        outcome.trace_id or "",
                        outcome.session_id_runtime or "",
                    ]
                    for outcome in failed_outcomes
                ],
            )
        )

    summary_md = report_dir / "summary.md"
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_json


@pytest.mark.e2e
@pytest.mark.eval_deterministic
@pytest.mark.network
def test_benchmark_1_input_guardrails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the deterministic input-guardrail benchmark and emit a local report."""
    if not DATASET_PATH.exists():
        pytest.fail(f"Benchmark dataset not found: {DATASET_PATH}")

    cases = _load_cases(DATASET_PATH)
    run_slug, report_dir, latest_dir = prepare_report_directories(ARTIFACTS_ROOT)
    outcomes: list[CaseOutcome] = []
    startup_error: str | None = None
    price_enrichment_status = "not_run"

    settings = _build_benchmark_settings()
    monkeypatch.setattr("customer_bot.config._build_settings", lambda: settings)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            app = create_app(enable_observability=True, run_startup_checks=True)
            with TestClient(app) as client:
                for case in cases:
                    runtime_session_id = resolve_runtime_session_id(run_slug, case.session_id)
                    outcomes.append(_run_case(client, case, runtime_session_id=runtime_session_id))
            price_enrichment_status = _enrich_costs_from_langfuse(outcomes, settings)
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
                        "price_enrichment_status": price_enrichment_status,
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
            "# Benchmark 1 Summary\n\n"
            f"- Benchmark: `{BENCHMARK_NAME}`\n"
            f"- Dataset: `{DATASET_PATH.relative_to(REPO_ROOT)}`\n"
            f"- Run Slug: `{run_slug}`\n"
            f"- Startup Error: {startup_error}\n",
            encoding="utf-8",
        )
        publish_latest_report(report_dir, latest_dir)
        pytest.fail(f"Benchmark startup failed. See report: {summary_json}")

    summary_json = _write_report(
        report_dir,
        run_slug,
        cases,
        outcomes,
        price_enrichment_status=price_enrichment_status,
    )
    publish_latest_report(report_dir, latest_dir)
    failed_cases = [outcome for outcome in outcomes if not outcome.passed]
    if failed_cases:
        pytest.fail(
            f"Benchmark mismatches detected in {len(failed_cases)} case(s). "
            f"See report: {summary_json}"
        )
