"""Runtime helpers for DeepEval-backed FastAPI end-to-end tests."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from unittest.mock import patch

from deepeval.test_case import LLMTestCase, ToolCall
from fastapi.testclient import TestClient

from customer_bot.api.deps import clear_dependency_caches
from customer_bot.api.main import create_app
from customer_bot.config import Settings
from tests.evals.config import EvalConfig
from tests.evals.dataset import ToolCallSpec, UnifiedGoldenCase
from tests.evals.langfuse_bridge import (
    TraceSnapshot,
    create_langfuse_client,
    wait_for_trace_snapshot,
)


@dataclass(slots=True)
class EvalResponse:
    """Normalized `/chat` response data used by the eval suite."""

    actual_output: str
    session_id: str
    trace_id: str
    status: str
    guardrail_reason: str | None
    handoff_required: bool
    retry_used: bool
    sanitized: bool
    completion_time: float


@dataclass(slots=True)
class EvalSuiteContext:
    """Reusable suite-scoped objects for one DeepEval test profile."""

    suite_name: str
    run_label: str
    settings: Settings
    client: TestClient
    langfuse_client: Any


def build_guardrail_settings(run_label: str, config: EvalConfig) -> Settings:
    """Build runtime settings for deterministic input-guardrail evaluation."""

    settings = Settings()
    settings.api.rate_limit.default_limit = "1000/minute"
    settings.api.rate_limit.chat_limit = "1000/minute"
    settings.memory.redis.key_prefix = f"customer-bot:deepeval:guardrails:{run_label}"
    settings.memory.redis.ttl_seconds = 300
    settings.guardrails.output.pii.enabled = False
    settings.guardrails.output.grounding.enabled = False
    settings.guardrails.output.bias.enabled = False
    settings.guardrails.output.rewrite.enabled = False
    settings.guardrails.global_.max_output_retries = 0
    settings.langfuse.fail_fast = True
    settings.langfuse.release = f"{config.langfuse.release_prefix}/guardrails/{run_label}"
    return settings


def build_agent_settings(run_label: str, config: EvalConfig) -> Settings:
    """Build runtime settings for agent/RAG DeepEval coverage."""

    settings = Settings()
    settings.api.rate_limit.default_limit = "1000/minute"
    settings.api.rate_limit.chat_limit = "1000/minute"
    settings.memory.redis.key_prefix = f"customer-bot:deepeval:agent:{run_label}"
    settings.memory.redis.ttl_seconds = 300
    # Keep the no-match product case deterministic for the golden dataset by
    # rejecting weak fuzzy matches that are otherwise acceptable in production.
    settings.retrieval.products.similarity_cutoff = 0.35
    settings.langfuse.fail_fast = True
    settings.langfuse.release = f"{config.langfuse.release_prefix}/agent/{run_label}"
    return settings


@contextmanager
def suite_context(
    *,
    suite_name: str,
    run_label: str,
    settings: Settings,
) -> Iterator[EvalSuiteContext]:
    """Create a reusable FastAPI test client plus Langfuse client for one suite."""

    clear_dependency_caches()
    with ExitStack() as stack:
        stack.enter_context(patch("customer_bot.api.deps.get_settings", return_value=settings))
        stack.enter_context(patch("customer_bot.config.get_settings", return_value=settings))
        app = create_app(enable_observability=True, run_startup_checks=True)
        langfuse_client = create_langfuse_client(settings)
        with TestClient(app) as client:
            yield EvalSuiteContext(
                suite_name=suite_name,
                run_label=run_label,
                settings=settings,
                client=client,
                langfuse_client=langfuse_client,
            )
    clear_dependency_caches()


def run_case(
    context: EvalSuiteContext,
    case: UnifiedGoldenCase,
) -> tuple[EvalResponse, TraceSnapshot]:
    """Execute one dataset case, including any setup turns, against the FastAPI app."""

    session_id = _resolve_runtime_session_id(context.run_label, case)
    for setup_turn in case.additional_metadata.setup_turns:
        setup_response = _post_chat(context.client, setup_turn.input, session_id)
        _assert_setup_turn(case.additional_metadata.case_id, setup_turn, setup_response)

    response = _post_chat(context.client, case.input, session_id)
    _flush_app_langfuse_client(context.client)
    if case.additional_metadata.case_type == "agent_e2e":
        trace_snapshot = wait_for_trace_snapshot(context.langfuse_client, response.trace_id)
    else:
        trace_snapshot = TraceSnapshot(retrieval_context=[], tools_called=[])
    return response, trace_snapshot


def validate_contract(case: UnifiedGoldenCase, response: EvalResponse) -> list[str]:
    """Compare the public response contract against dataset expectations."""

    expected = case.additional_metadata
    failures: list[str] = []
    if response.status != expected.expected_status:
        failures.append(
            f"status mismatch: expected={expected.expected_status} actual={response.status}"
        )
    if response.guardrail_reason != expected.expected_guardrail_reason:
        failures.append(
            "guardrail_reason mismatch: "
            f"expected={expected.expected_guardrail_reason} actual={response.guardrail_reason}"
        )
    if response.handoff_required != expected.expected_handoff_required:
        failures.append(
            "handoff_required mismatch: "
            f"expected={expected.expected_handoff_required} actual={response.handoff_required}"
        )
    if response.retry_used != expected.expected_retry_used:
        failures.append(
            "retry_used mismatch: "
            f"expected={expected.expected_retry_used} actual={response.retry_used}"
        )
    if not response.trace_id:
        failures.append("trace_id missing from /chat response")
    return failures


def build_test_case(
    *,
    case: UnifiedGoldenCase,
    response: EvalResponse,
    trace_snapshot: TraceSnapshot,
) -> LLMTestCase:
    """Convert one executed eval case into a DeepEval `LLMTestCase`."""

    return LLMTestCase(
        input=case.input,
        actual_output=response.actual_output,
        expected_output=case.expected_output,
        context=case.context,
        retrieval_context=trace_snapshot.retrieval_context or None,
        metadata={
            "case_id": case.additional_metadata.case_id,
            "case_type": case.additional_metadata.case_type,
            "trace_id": response.trace_id,
            "status": response.status,
        },
        tools_called=trace_snapshot.tools_called or None,
        expected_tools=_to_tool_calls(case.expected_tools),
        comments=case.comments,
        completion_time=response.completion_time,
        name=case.additional_metadata.case_id,
        tags=[case.additional_metadata.case_type],
    )


def _post_chat(client: TestClient, user_message: str, session_id: str) -> EvalResponse:
    payload = {"user_message": user_message, "session_id": session_id}
    started_at = perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        response = client.post("/chat", json=payload)
    completion_time = round(perf_counter() - started_at, 4)
    if response.status_code != 200:
        raise AssertionError(f"unexpected http status: expected=200 actual={response.status_code}")

    body = response.json()
    meta = body.get("meta") or {}
    trace_id = body.get("trace_id")
    if not isinstance(trace_id, str) or not trace_id.strip():
        raise AssertionError("trace_id missing from /chat response")

    answer = body.get("answer")
    session = body.get("session_id")
    if not isinstance(answer, str) or not isinstance(session, str):
        raise AssertionError("response body is missing required answer/session_id fields")

    return EvalResponse(
        actual_output=answer,
        session_id=session,
        trace_id=trace_id,
        status=str(meta.get("status")),
        guardrail_reason=meta.get("guardrail_reason"),
        handoff_required=bool(body.get("handoff_required")),
        retry_used=bool(meta.get("retry_used")),
        sanitized=bool(meta.get("sanitized")),
        completion_time=completion_time,
    )


def _assert_setup_turn(case_id: str, expected: Any, actual: EvalResponse) -> None:
    failures: list[str] = []
    if actual.status != expected.expected_status:
        failures.append(f"status expected={expected.expected_status} actual={actual.status}")
    if actual.guardrail_reason != expected.expected_guardrail_reason:
        failures.append(
            "guardrail_reason expected="
            f"{expected.expected_guardrail_reason} actual={actual.guardrail_reason}"
        )
    if actual.handoff_required != expected.expected_handoff_required:
        failures.append(
            "handoff_required expected="
            f"{expected.expected_handoff_required} actual={actual.handoff_required}"
        )
    if actual.retry_used != expected.expected_retry_used:
        failures.append(
            f"retry_used expected={expected.expected_retry_used} actual={actual.retry_used}"
        )
    if failures:
        raise AssertionError(f"setup turn failed for case {case_id}: {'; '.join(failures)}")


def _resolve_runtime_session_id(run_label: str, case: UnifiedGoldenCase) -> str:
    session_seed = case.additional_metadata.session_id or case.additional_metadata.case_id
    return f"{run_label}__{session_seed}"


def _flush_app_langfuse_client(client: TestClient) -> None:
    langfuse_client = getattr(client.app.state, "langfuse_client", None)
    if langfuse_client is None:
        return
    flush = getattr(langfuse_client, "flush", None)
    if callable(flush):
        flush()


def _to_tool_calls(tool_specs: list[ToolCallSpec] | None) -> list[ToolCall] | None:
    if not tool_specs:
        return None
    return [
        ToolCall(
            name=tool_spec.name,
            description=tool_spec.description,
            reasoning=tool_spec.reasoning,
            output=tool_spec.output,
            input_parameters=tool_spec.input_parameters,
        )
        for tool_spec in tool_specs
    ]
