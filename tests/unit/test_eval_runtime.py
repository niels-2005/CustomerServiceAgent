from __future__ import annotations

import re

from tests.evals.config import load_eval_config
from tests.evals.conftest import _build_run_label
from tests.evals.runtime import build_agent_settings, build_guardrail_settings


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
