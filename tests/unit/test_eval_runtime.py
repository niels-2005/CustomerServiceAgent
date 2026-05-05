from __future__ import annotations

import re

from deepeval.test_case import ToolCall

from tests.evals.config import load_eval_config
from tests.evals.conftest import _build_run_label
from tests.evals.dataset import AgentGoldenCase
from tests.evals.langfuse_bridge import TraceSnapshot
from tests.evals.runtime import (
    EvalResponse,
    build_agent_settings,
    build_guardrail_settings,
    build_test_case,
)


def test_build_run_label_uses_utc_minute_precision() -> None:
    run_label = _build_run_label()

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}Z", run_label)


def test_eval_settings_share_one_langfuse_version_per_run() -> None:
    eval_config = load_eval_config()
    run_label = "2026-05-03T14-25Z"

    guardrail_settings = build_guardrail_settings(run_label, eval_config)
    agent_settings = build_agent_settings(run_label, eval_config)

    assert guardrail_settings.langfuse.version == run_label
    assert agent_settings.langfuse.version == run_label
    assert (
        guardrail_settings.langfuse.release == f"{eval_config.langfuse.release_prefix}/{run_label}"
    )
    assert agent_settings.langfuse.release == f"{eval_config.langfuse.release_prefix}/{run_label}"


def test_build_test_case_preserves_explicit_empty_tool_contract() -> None:
    case = AgentGoldenCase(
        case_id="answer_001",
        input="Wie setze ich mein Passwort zurück?",
        expected_output="Passwort vergessen.",
        expected_tools=[],
    )
    response = EvalResponse(
        actual_output="Passwort vergessen.",
        session_id="session-1",
        trace_id="trace-1",
        status="answered",
        guardrail_reason=None,
        handoff_required=False,
        retry_used=False,
        sanitized=False,
    )

    test_case = build_test_case(
        case=case,
        response=response,
        trace_snapshot=TraceSnapshot(
            retrieval_context=["faq_7: Passwort vergessen."],
            tools_called=[],
        ),
    )

    assert test_case.expected_tools == []
    assert test_case.tools_called == []


def test_build_test_case_omits_tool_fields_when_tool_contract_is_unspecified() -> None:
    case = AgentGoldenCase(
        case_id="answer_002",
        input="Wie setze ich mein Passwort zurück?",
        expected_output="Passwort vergessen.",
        expected_tools=None,
    )
    response = EvalResponse(
        actual_output="Passwort vergessen.",
        session_id="session-1",
        trace_id="trace-1",
        status="answered",
        guardrail_reason=None,
        handoff_required=False,
        retry_used=False,
        sanitized=False,
    )

    test_case = build_test_case(
        case=case,
        response=response,
        trace_snapshot=TraceSnapshot(
            retrieval_context=["faq_7: Passwort vergessen."],
            tools_called=[ToolCall(name="faq_lookup")],
        ),
    )

    assert test_case.expected_tools is None
