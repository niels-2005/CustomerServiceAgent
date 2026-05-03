"""Golden dataset loaders for the DeepEval end-to-end suites."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DATASET_DIR = Path(__file__).resolve().parents[2] / "datasets" / "benchmark"
GUARDRAIL_DATASET_PATH = DATASET_DIR / "deepeval_guardrails.json"
AGENT_DATASET_PATH = DATASET_DIR / "deepeval_agent_e2e.json"


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
    expected_status: str = Field(min_length=1)
    expected_guardrail_reason: str | None = None
    expected_handoff_required: bool
    expected_retry_used: bool = False


class GuardrailGoldenCase(BaseModel):
    """Deterministic input-guardrail case evaluated via exact string match."""

    case_id: str = Field(min_length=1)
    input: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    session_id: str | None = None
    setup_turns: list[SetupTurn] = Field(default_factory=list)


class AgentGoldenCase(BaseModel):
    """Agent/RAG case evaluated with LLM-judge and tool-aware metrics."""

    case_id: str = Field(min_length=1)
    input: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    context: list[str] | None = None
    expected_tools: list[ToolCallSpec] | None = None
    comments: str | None = None
    expected_status: str = Field(default="answered", min_length=1)
    expected_guardrail_reason: str | None = None
    expected_handoff_required: bool = False
    expected_retry_used: bool = False
    session_id: str | None = None
    setup_turns: list[SetupTurn] = Field(default_factory=list)


def load_guardrail_cases(path: Path = GUARDRAIL_DATASET_PATH) -> list[GuardrailGoldenCase]:
    """Load the deterministic guardrail dataset from JSON."""

    cases = [GuardrailGoldenCase.model_validate(item) for item in _load_items(path)]
    if not cases:
        raise ValueError("Guardrail eval dataset has no cases.")
    return cases


def load_agent_cases(path: Path = AGENT_DATASET_PATH) -> list[AgentGoldenCase]:
    """Load the agent/RAG end-to-end dataset from JSON."""

    cases = [AgentGoldenCase.model_validate(item) for item in _load_items(path)]
    if not cases:
        raise ValueError("Agent eval dataset has no cases.")
    return cases


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("cases")
    if not isinstance(items, list):
        raise ValueError("Eval dataset must contain a top-level list or a 'cases' array.")
    return items
