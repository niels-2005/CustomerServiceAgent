from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from tests.evals.config import EvalConfig, load_eval_config
from tests.evals.runtime import (
    EvalSuiteContext,
    build_agent_settings,
    build_guardrail_settings,
    suite_context,
)


def _build_run_label() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%MZ")


@pytest.fixture(scope="session")
def eval_config() -> EvalConfig:
    return load_eval_config()


@pytest.fixture(scope="session")
def eval_run_label() -> str:
    return _build_run_label()


@pytest.fixture(scope="session")
def guardrail_suite(eval_config: EvalConfig, eval_run_label: str) -> Iterator[EvalSuiteContext]:
    settings = build_guardrail_settings(eval_run_label, eval_config)
    with suite_context(
        suite_name="guardrail_deterministic",
        run_label=eval_run_label,
        settings=settings,
    ) as context:
        yield context


@pytest.fixture(scope="session")
def agent_suite(eval_config: EvalConfig, eval_run_label: str) -> Iterator[EvalSuiteContext]:
    settings = build_agent_settings(eval_run_label, eval_config)
    with suite_context(
        suite_name="agent_e2e",
        run_label=eval_run_label,
        settings=settings,
    ) as context:
        yield context
