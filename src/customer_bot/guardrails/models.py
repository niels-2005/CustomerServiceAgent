from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

InputAction = Literal["allow", "blocked", "handoff"]
OutputAction = Literal["allow", "rewrite", "fallback"]
GuardrailDecision = Literal["allow", "block", "handoff", "rewrite", "fallback"]


@dataclass(slots=True)
class GuardrailCheck:
    name: str
    decision: GuardrailDecision
    reason: str | None = None
    rewrite_hint: str | None = None
    triggered: bool = False


@dataclass(slots=True)
class GuardrailInputResult:
    action: InputAction
    reason: str | None
    message: str | None
    sanitized_user_message: str
    checks: list[GuardrailCheck] = field(default_factory=list)
    sanitized: bool = False


@dataclass(slots=True)
class GuardrailOutputResult:
    action: OutputAction
    reason: str | None
    rewrite_hint: str | None
    checks: list[GuardrailCheck] = field(default_factory=list)
    sanitized: bool = False


@dataclass(slots=True)
class GuardrailRewriteResult:
    answer: str
    sanitized: bool = False
