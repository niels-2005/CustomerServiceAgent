# Guardrails AI Docs Notes

This file is a reconstructed working summary of the Guardrails AI documentation that was previously present in this repository.
It is not guaranteed to be byte-identical to the deleted original file.
It is intended as a local implementation reference for this project.

## What Guardrails Is

Guardrails is a Python framework for adding input/output validation and remediation around LLM applications.

Core capabilities:

- input guards
- output guards
- structured output generation and validation
- custom validators
- hub-installed validators
- guard execution history and validation logs
- async validation via `AsyncGuard`

## Main Concepts

### Guard

The `Guard` object is the main orchestration interface.
It can:

- validate text or structured data
- call an LLM directly
- validate user-provided LLM output via `parse(...)` or `validate(...)`

Important interfaces:

- `guard(...)`
- `guard.parse(...)`
- `guard.validate(...)`

### AsyncGuard

Use `AsyncGuard` for asynchronous validation and better concurrency.

Important takeaways:

- `Guard` no longer should be relied on for async behavior
- `AsyncGuard` is the preferred async path
- async validation allows validators on the same value to run concurrently
- for unstructured text, validators can run concurrently on the same field
- exception-producing validators fail early

For this project:

- input guards should use `AsyncGuard`
- output guards should use `AsyncGuard`
- we should keep orchestration outside the guards so pipeline policy remains explicit

## Validation Model

Validators return either:

- `PassResult`
- `FailResult`

General pattern:

- pass => value is accepted
- fail => `on_fail` policy determines what happens next

## on_fail Actions

Documented `on_fail` behaviors include:

- `noop`
- `exception`
- `reask`
- `fix`
- `filter`
- `refrain`
- `fix_reask`
- custom function

Project guidance:

- for complex product logic, prefer exception/result-based orchestration outside the validator
- do not bury core application branching inside validator-local retries
- use explicit pipeline handling in the application service

For this project:

- input guards should effectively behave as block/handoff decisions, not auto-reask
- output guards may trigger exactly one external rewrite step
- do not use unlimited or implicit correction loops

## Runtime Metadata

Validators can depend on runtime metadata passed to the guard call.

Metadata is useful for:

- passing dynamic sources/evidence
- passing per-call settings
- providing extra evaluation context

Example pattern from docs:

- provenance validators can receive `sources`
- pii validators can receive `pii_entities`
- multiple validators can share one metadata dictionary

For this project:

- metadata is useful for grounding checks
- metadata can carry evidence snippets, chat context, or PII entity lists

## Custom Validators

Guardrails supports custom validators via classes that inherit from `Validator`.

Typical pattern:

```python
from guardrails.validators import (
    Validator,
    ValidationResult,
    PassResult,
    FailResult,
    register_validator,
)

@register_validator(name="custom/my-validator", data_type="string")
class MyValidator(Validator):
    def _validate(self, value: str, metadata: dict) -> ValidationResult:
        if some_check(value):
            return PassResult()
        return FailResult(error_message="Validation failed")
```
```

Useful notes:

- custom validators can be algorithmic or LLM-based
- a `FailResult` may include a fix value
- validators can be written as plain functions for simpler cases
- custom validators should still keep logic deterministic where possible

For this project:

- domain-specific guards should be custom validators
- product policy should still live in application orchestration, not hidden inside validators

## Structured Output Guidance

Guardrails supports structured output and schema validation.

Important project takeaway:

- use strict structured outputs for LLM-based guard decisions
- avoid prose parsing
- define explicit schemas for decisions

Recommended decision shape for LLM-based project guards:

- `decision`
- `score`
- `reason`
- `rewrite_hint` where applicable

## Async and Concurrency Notes

Key notes from the docs:

- `AsyncGuard` is the preferred async path
- async validation can run validators concurrently
- exception-based validators interrupt processing early
- fixes/reasks are handled after async futures are collected depending on action type

Project decision:

- use explicit pipeline ordering:
  - input PII first
  - remaining input guards in parallel
  - output PII first
  - remaining output guards in parallel

This is intentionally stricter than “run everything concurrently” because it avoids sending sensitive data to downstream LLM validators or third-party APIs.

## Error Handling

Guardrails docs emphasize:

- validation failures are available through guard history/logs
- exception-based handling is often better for complex applications

Project decision:

- fail closed on guard infrastructure problems
- do not silently allow if a guard model/provider fails
- output-side technical failures should produce safe fallback behavior

## Guard History and Logs

Guard executions are logged internally.

Important references from docs:

- `guard.history`
- `guard.history.last`
- `iterations`
- `failed_validations`
- validator logs

Project use:

- useful for debugging in tests
- runtime product tracing should primarily use Langfuse spans/generations

## Performance Notes

Guardrails docs recommend:

- use `AsyncGuard` for best performance
- keep validation orchestration efficient
- run cheap checks before expensive ones

Project interpretation:

- run PII first because it is both security-critical and a hard gate
- only run LLM-based secondary checks if the content is safe to send

## Telemetry and Observability

Guardrails supports OpenTelemetry.
The docs highlight:

- latency tracking
- success/fail rates
- validator-level monitoring

Project decision:

- keep OpenInference + Langfuse as the main observability path
- instrument guardrail stages explicitly in Langfuse
- do not introduce a separate Guardrails server for v1

## Guardrails Server

The docs describe a Guardrails server that can run guard definitions behind OpenAI-compatible endpoints.

Project decision:

- do not use Guardrails Server in v1
- run Guardrails in-process in the application

Reason:

- simpler deployment
- easier local iteration
- easier coordination with current FastAPI + Langfuse + LlamaIndex setup

## Relevant Implementation Patterns for This Project

### Input Guards

Needed before agent call:

- escalation
- prompt injection
- topic relevance
- secret/PII detection

### Output Guards

Needed after agent call:

- sensitive data detection
- grounding / hallucination / relevance
- bias

### Retry Strategy

Docs mention reask/fix patterns, but this project should not use implicit guard-internal loops for primary product logic.

Project decision:

- one explicit rewrite step outside the guard
- no full agent rerun
- no repeated hidden guard retries

## Working Decisions for This Repo

- use Guardrails AI in-application
- use `AsyncGuard` for async validation paths
- use strict structured outputs for LLM-based decision guards
- use custom validators for project-specific behavior
- use hub validator for PII detection where useful
- keep orchestration logic in app services
- keep all user-facing policy explicit and env-configurable

## Practical Summary for the Implementer

If you are implementing guardrails in this repo:

1. Read `PLAN.md` first.
2. Use this file as Guardrails AI background/reference.
3. Prefer `AsyncGuard`.
4. Prefer explicit result handling over hidden reask logic.
5. Use custom validators for domain-specific guards.
6. Use strict structured outputs for LLM-based guard decisions.
7. Keep the pipeline ordering and fail-closed policy from `PLAN.md`.
