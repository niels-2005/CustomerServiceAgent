"""Unified golden dataset loader for DeepEval end-to-end suites."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "benchmark" / "deepeval_e2e_goldens.json"
)


class ToolCallSpec(BaseModel):
    """Serializable tool-call expectation stored in the golden dataset."""

    name: str = Field(min_length=1)
    description: str | None = None
    reasoning: str | None = None
    input_parameters: dict[str, Any] | None = None
    output: Any | None = None


class SetupTurn(BaseModel):
    """One preparatory request executed before the scored turn."""

    input: str = Field(min_length=1)
    assistant_message: str | None = None
    seed_history_only: bool = False
    expected_status: str = Field(min_length=1)
    expected_guardrail_reason: str | None = None
    expected_handoff_required: bool
    expected_retry_used: bool = False


class EvalCaseMetadata(BaseModel):
    """App-specific metadata used to route and validate one eval case."""

    case_id: str = Field(min_length=1)
    case_type: str = Field(pattern="^(guardrail_deterministic|agent_e2e)$")
    expected_status: str = Field(min_length=1)
    expected_guardrail_reason: str | None = None
    expected_handoff_required: bool
    expected_retry_used: bool = False
    session_id: str | None = None
    setup_turns: list[SetupTurn] = Field(default_factory=list)


class UnifiedGoldenCase(BaseModel):
    """One unified golden row that can be converted into an LLMTestCase."""

    input: str = Field(min_length=1)
    expected_output: str | None = None
    context: list[str] | None = None
    expected_tools: list[ToolCallSpec] | None = None
    comments: str | None = None
    additional_metadata: EvalCaseMetadata


def load_cases(path: Path = DATASET_PATH) -> list[UnifiedGoldenCase]:
    """Load the unified DeepEval golden dataset from JSON."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("cases")
    if not isinstance(items, list):
        raise ValueError("Unified eval dataset must contain a top-level list or a 'cases' array.")
    cases = [UnifiedGoldenCase.model_validate(item) for item in items]
    if not cases:
        raise ValueError("Unified eval dataset has no cases.")
    return cases


def select_cases(case_type: str, path: Path = DATASET_PATH) -> list[UnifiedGoldenCase]:
    """Return only dataset rows belonging to the requested evaluation profile."""

    return [case for case in load_cases(path) if case.additional_metadata.case_type == case_type]
