"""Shared guardrail result types exchanged across the guardrail subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

InputAction = Literal["allow", "blocked", "handoff"]
OutputAction = Literal["allow", "rewrite", "fallback"]
GuardrailDecision = Literal["allow", "block", "handoff", "rewrite", "fallback"]
GuardrailDecisionSource = Literal["pii_detector", "heuristic", "llm"]


@dataclass(slots=True)
class GuardrailCheck:
    """Decision emitted by one individual guard."""

    name: str
    decision: GuardrailDecision
    reason: str | None = None
    rewrite_hint: str | None = None
    triggered: bool = False
    decision_source: GuardrailDecisionSource = "llm"
    llm_called: bool = True


@dataclass(slots=True)
class GuardrailInputResult:
    """Normalized result returned by the input guard pipeline."""

    action: InputAction
    reason: str | None
    message: str | None
    sanitized_user_message: str
    checks: list[GuardrailCheck] = field(default_factory=list)
    sanitized: bool = False


@dataclass(slots=True)
class GuardrailOutputResult:
    """Normalized result returned by the output guard pipeline."""

    action: OutputAction
    reason: str | None
    rewrite_hint: str | None
    checks: list[GuardrailCheck] = field(default_factory=list)
    sanitized: bool = False


@dataclass(slots=True)
class GuardrailRewriteResult:
    """Result returned by the rewrite service after post-processing an answer."""

    answer: str
    sanitized: bool = False
