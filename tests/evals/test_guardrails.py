from __future__ import annotations

import pytest

from tests.evals.config import EvalConfig
from tests.evals.dataset import UnifiedGoldenCase, select_cases
from tests.evals.deepeval_runner import build_guardrail_metrics, measure_metrics
from tests.evals.langfuse_bridge import publish_metric_outcomes
from tests.evals.runtime import EvalSuiteContext, build_test_case, run_case, validate_contract

pytestmark = [pytest.mark.e2e, pytest.mark.eval_deterministic]

GUARDRAIL_CASES = select_cases("guardrail_deterministic")


@pytest.mark.parametrize(
    "case",
    GUARDRAIL_CASES,
    ids=[case.additional_metadata.case_id for case in GUARDRAIL_CASES],
)
def test_input_guardrails(
    case: UnifiedGoldenCase,
    guardrail_suite: EvalSuiteContext,
    eval_config: EvalConfig,
) -> None:
    response, trace_snapshot = run_case(guardrail_suite, case)
    test_case = build_test_case(case=case, response=response, trace_snapshot=trace_snapshot)

    failures = validate_contract(case, response)
    metric_outcomes, metric_failures = measure_metrics(
        test_case,
        build_guardrail_metrics(eval_config),
    )
    failures.extend(metric_failures)

    publish_metric_outcomes(
        client=guardrail_suite.langfuse_client,
        trace_id=response.trace_id,
        score_prefix=eval_config.langfuse.score_prefix,
        run_label=guardrail_suite.run_label,
        suite_name=guardrail_suite.suite_name,
        case_id=case.additional_metadata.case_id,
        outcomes=metric_outcomes,
        case_passed=not failures,
        case_failure_comment=" | ".join(failures) if failures else None,
    )

    assert not failures, " ; ".join(failures)
