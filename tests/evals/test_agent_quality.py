from __future__ import annotations

import pytest

from tests.evals.config import EvalConfig
from tests.evals.dataset import UnifiedGoldenCase, select_cases
from tests.evals.deepeval_runner import build_agent_metrics, measure_metrics
from tests.evals.langfuse_bridge import publish_metric_outcomes
from tests.evals.runtime import EvalSuiteContext, build_test_case, run_case, validate_contract

pytestmark = [pytest.mark.e2e, pytest.mark.eval_llm_judge, pytest.mark.network]

AGENT_CASES = select_cases("agent_e2e")


@pytest.mark.parametrize(
    "case",
    AGENT_CASES,
    ids=[case.additional_metadata.case_id for case in AGENT_CASES],
)
def test_agent_quality(
    case: UnifiedGoldenCase,
    agent_suite: EvalSuiteContext,
    eval_config: EvalConfig,
) -> None:
    response, trace_snapshot = run_case(agent_suite, case)
    test_case = build_test_case(case=case, response=response, trace_snapshot=trace_snapshot)

    failures = validate_contract(case, response)
    metric_outcomes, metric_failures = measure_metrics(
        test_case,
        build_agent_metrics(
            eval_config,
            include_contextual_relevancy=trace_snapshot.has_grounded_retrieval_context,
            openai_api_key=agent_suite.settings.openai_api_key,
        ),
    )
    failures.extend(metric_failures)

    publish_metric_outcomes(
        client=agent_suite.langfuse_client,
        trace_id=response.trace_id,
        score_prefix=eval_config.langfuse.score_prefix,
        run_label=agent_suite.run_label,
        suite_name=agent_suite.suite_name,
        case_id=case.additional_metadata.case_id,
        outcomes=metric_outcomes,
        case_passed=not failures,
        case_failure_comment=" | ".join(failures) if failures else None,
    )

    assert not failures, " ; ".join(failures)
