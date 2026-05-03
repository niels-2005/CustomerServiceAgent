"""Langfuse helpers for trace extraction and score publishing in eval tests."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from deepeval.test_case import ToolCall
from langfuse import Langfuse

from customer_bot.agent.tooling import FAQ_TOOL_NAME, PRODUCT_TOOL_NAME
from customer_bot.agent.tracing import (
    FAQ_NO_MATCH_EVIDENCE,
    PRODUCT_NO_MATCH_EVIDENCE,
    _ToolTraceFormatter,
)
from customer_bot.config import Settings

OBSERVATION_TIMEOUT_SECONDS = 30.0
OBSERVATION_POLL_INTERVAL_SECONDS = 2.0
SUPPORTED_TOOL_NAMES = {FAQ_TOOL_NAME, PRODUCT_TOOL_NAME}
NO_MATCH_SENTINELS = {FAQ_NO_MATCH_EVIDENCE, PRODUCT_NO_MATCH_EVIDENCE}


@dataclass(slots=True)
class MetricOutcome:
    """Normalized metric result that can be asserted and published."""

    score_name: str
    value: float
    threshold: float
    passed: bool
    reason: str | None


@dataclass(slots=True)
class TraceSnapshot:
    """Langfuse trace data needed to build DeepEval test cases."""

    retrieval_context: list[str]
    tools_called: list[ToolCall]

    @property
    def has_grounded_retrieval_context(self) -> bool:
        """Return whether the retrieval context contains grounded evidence."""

        return any(item not in NO_MATCH_SENTINELS for item in self.retrieval_context)


def create_langfuse_client(settings: Settings) -> Langfuse:
    """Create a Langfuse client and fail clearly when credentials are missing."""

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        raise RuntimeError("Langfuse credentials are required for DeepEval e2e tests.")

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse.host,
    )


def wait_for_trace_snapshot(client: Langfuse, trace_id: str) -> TraceSnapshot:
    """Poll Langfuse until the tool observations required for evals are visible."""

    formatter = _ToolTraceFormatter()
    deadline = time.monotonic() + OBSERVATION_TIMEOUT_SECONDS
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            observations = client.api.legacy.observations_v1.get_many(trace_id=trace_id, limit=100)
            tool_calls: list[ToolCall] = []
            retrieval_context: list[str] = []
            seen_tool_calls: set[str] = set()
            for observation in observations.data:
                tool_call_payload = _extract_tool_call_payload(observation)
                if tool_call_payload is None:
                    continue
                tool_call_key = _build_tool_call_key(tool_call_payload)
                if tool_call_key in seen_tool_calls:
                    continue
                seen_tool_calls.add(tool_call_key)
                retrieval_context.extend(formatter.extract_evidence(tool_call_payload))
                tool_calls.append(
                    ToolCall(
                        name=tool_call_payload["tool_name"],
                        input_parameters=_normalize_input_parameters(tool_call_payload["tool_input"]),
                        output=tool_call_payload["tool_output"],
                    )
                )

            if tool_calls:
                return TraceSnapshot(retrieval_context=retrieval_context, tools_called=tool_calls)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            last_error = exc
        time.sleep(OBSERVATION_POLL_INTERVAL_SECONDS)

    detail = f"{type(last_error).__name__}: {last_error}" if last_error is not None else "timeout"
    raise RuntimeError(
        "Langfuse trace observations were not available within "
        f"{OBSERVATION_TIMEOUT_SECONDS:.0f}s ({detail})."
    )


def publish_metric_outcomes(
    *,
    client: Langfuse,
    trace_id: str,
    score_prefix: str,
    run_label: str,
    suite_name: str,
    case_id: str,
    outcomes: list[MetricOutcome],
    case_passed: bool,
    case_failure_comment: str | None,
) -> None:
    """Attach metric scores and the aggregate case result to a Langfuse trace."""

    score_timestamp = datetime.now(UTC)
    for outcome in outcomes:
        score_name = f"{score_prefix}.{outcome.score_name}"
        client.create_score(
            trace_id=trace_id,
            name=score_name,
            value=outcome.value,
            data_type="NUMERIC",
            score_id=f"{trace_id}:{score_name}",
            comment=outcome.reason,
            metadata={
                "passed": outcome.passed,
                "threshold": outcome.threshold,
                "suite_name": suite_name,
                "run_label": run_label,
                "case_id": case_id,
            },
            timestamp=score_timestamp,
        )

    case_score_name = f"{score_prefix}.case_pass"
    client.create_score(
        trace_id=trace_id,
        name=case_score_name,
        value=1 if case_passed else 0,
        data_type="BOOLEAN",
        score_id=f"{trace_id}:{case_score_name}",
        comment=case_failure_comment,
        metadata={
            "suite_name": suite_name,
            "run_label": run_label,
            "case_id": case_id,
        },
        timestamp=score_timestamp,
    )
    client.flush()


def _get_attr(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _extract_tool_call_payload(observation: Any) -> dict[str, Any] | None:
    observation_type = str(_get_attr(observation, "type") or "").upper()
    if observation_type != "TOOL":
        return None

    tool_name = _resolve_tool_name(observation)
    if tool_name not in SUPPORTED_TOOL_NAMES:
        return None

    tool_input = _extract_tool_input(observation)
    tool_output = _extract_tool_output(observation)
    return {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "is_error": str(_get_attr(observation, "level") or "").upper() == "ERROR",
    }


def _resolve_tool_name(observation: Any) -> str:
    raw_name = str(_get_attr(observation, "name") or "").strip()
    if raw_name in SUPPORTED_TOOL_NAMES:
        return raw_name

    metadata = _extract_json(_get_attr(observation, "metadata"))
    if isinstance(metadata, dict):
        attributes = metadata.get("attributes")
        if isinstance(attributes, dict):
            attribute_tool_name = attributes.get("tool.name")
            if isinstance(attribute_tool_name, str):
                return attribute_tool_name.strip()

    return raw_name


def _extract_tool_input(observation: Any) -> Any:
    tool_input = _extract_json(_get_attr(observation, "input"))
    if not isinstance(tool_input, dict):
        return tool_input

    kwargs = tool_input.get("kwargs")
    if isinstance(kwargs, dict):
        return kwargs
    return tool_input


def _extract_tool_output(observation: Any) -> Any:
    tool_output = _extract_json(_get_attr(observation, "output"))
    if not isinstance(tool_output, dict):
        return tool_output

    raw_output = _extract_json(tool_output.get("raw_output"))
    if raw_output is not None:
        return raw_output
    return tool_output


def _extract_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _build_tool_call_key(tool_call_payload: dict[str, Any]) -> str:
    return json.dumps(tool_call_payload, ensure_ascii=False, sort_keys=True, default=str)


def _normalize_input_parameters(value: Any) -> dict[str, Any] | None:
    parsed = _extract_json(value)
    if isinstance(parsed, dict):
        return parsed
    if parsed is None:
        return None
    return {"value": parsed}
