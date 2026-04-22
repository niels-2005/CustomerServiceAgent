# Guardrails Integration Plan

## Purpose

This file is the execution plan for integrating Guardrails AI into the application.
It is written so that a new agent can read only this file plus the referenced local files and implement the work correctly without prior conversation context.

This plan is intentionally decision-complete for v1.

Before making implementation changes, the implementing agent must first read, if present:

- `PLAN.md`
- `GUARDRAILS_AI_DOCS.md`
- `GUARDRAILS_AI_IN_HUB.md`

Those files are the local planning/reference bundle for this feature.
If one of them is missing, use the remaining files plus current repo code as the source of truth and do not invent undocumented behavior.

## Current State

### Existing request flow

- `POST /chat` currently accepts `user_message` and optional `session_id`.
- `ChatService` in `src/customer_bot/chat/service.py`:
  - resolves/generates `session_id`
  - loads session history from memory backend
  - calls `AgentService.answer(...)`
  - appends raw user message and final assistant answer to memory
  - returns `ChatResult(answer, session_id)`
- `AgentService` in `src/customer_bot/agent/service.py`:
  - builds a `FunctionAgent`
  - runs LlamaIndex agent execution
  - uses Langfuse/OpenInference tracing
  - returns only a final answer string
- API response model in `src/customer_bot/api/models.py` currently contains only:
  - `answer`
  - `session_id`

### Existing observability

- `src/customer_bot/observability.py` initializes Langfuse.
- `src/customer_bot/agent/tracing.py` creates the current root observation and nested tool observations.
- OpenInference instrumentation for LlamaIndex is already present and must remain the baseline.

### Existing constraints

- Repo rules are in `AGENTS.md`.
- `README.md` and `.env.example` are source of truth for runtime configuration.
- Config changes must stay synchronized across code, `README.md`, and `.env.example`.
- No hidden defaults for runtime behavior.

## Goal

Add Guardrails AI around the chat pipeline with:

- input guardrails before the agent
- output guardrails after the agent
- explicit policy decisions for blocked, handoff, answered, and fallback outcomes
- full Langfuse visibility across input guards, agent, output guards, and rewrite step
- explicit env-driven configuration

Keep the design simple and conservative for v1.

## Final v1 Decisions

### Request pipeline

Execution order:

1. Start root chat trace with sanitized input
2. Run input `SecretPII` guard first
3. If input PII passes, run remaining input guards in parallel:
   - `PromptInjectionGuard`
   - `TopicRelevanceGuard`
   - `EscalationGuard`
4. If allowed, run agent
5. Run output `SensitiveData` guard first
6. If output PII passes, run remaining output guards in parallel:
   - `GroundingGuard`
   - `BiasGuard`
7. If output validation fails, run exactly one separate rewrite step
8. Re-run output guards on rewritten output
9. If still failing, return safe fallback

### Status outcomes

`POST /chat` must return one of:

- `answered`
- `blocked`
- `handoff`
- `fallback`

### Input decision priority

Priority is deterministic and fixed:

1. `blocked(secret_pii)`
2. `blocked(prompt_injection)`
3. `blocked(off_topic)`
4. `handoff(escalation)`
5. `allow`

### Memory policy

This is fixed for v1:

- `answered`: save final approved assistant answer
- `fallback`: save final safe fallback answer
- `blocked`: save only the safe system/block response
- `handoff`: save only the safe handoff response
- if request was blocked due to sensitive PII/secrets, do not store the raw sensitive user text

### Guard failure policy

Global policy is `fail closed`.

If a guard fails technically, for example:

- timeout
- provider/API error
- invalid structured output
- internal guard exception

Then:

- input side returns blocked/handoff-safe behavior, never implicit allow
- output side returns configured safe fallback
- frontend gets the existing configured fallback text for technical failures

### Retry policy

- Exactly one retry only
- Retry is a separate rewrite step, not a hidden guard-internal retry
- Retry does not re-run tools
- Retry does not re-run the full agent
- Retry uses the same evidence and a `rewrite_hint` from failed output guards

### Structured output policy

All LLM-based guards must use strict structured output.

Do not use free-text guard decisions.
Do not rely on heuristic parsing of prose.

### Escalation behavior

`EscalationGuard` is block/handoff only for v1.
It does not suggest follow-up frontend actions like `open_ticket` yet.

### Topic relevance behavior

`TopicRelevanceGuard` returns an off-topic block plus a helpful configured hint such as:

"Ich kann Fragen zu Produkten, Konto, Rechnung und Support beantworten."

This help text must be env-configurable.

## Provider and Model Configuration

### Existing provider roles

- `LLM_PROVIDER` remains for the actual FAQ agent
- `EMBEDDING_PROVIDER` remains for embeddings/retrieval

### New provider role

Introduce:

- `GUARDRAIL_PROVIDER`

For v1:

- only `openai` is supported

All LLM-based guards and the rewrite step must use `GUARDRAIL_PROVIDER`.

### Central OpenAI guardrail model config

Do not create separate OpenAI model parameters per individual guard.
Use one central guardrail OpenAI model config shared by:

- `PromptInjectionGuard`
- `TopicRelevanceGuard`
- `EscalationGuard` if it uses LLM classification
- `GroundingGuard`
- `BiasGuard`
- `RewriteStep`

Required config:

- `GUARDRAIL_PROVIDER`
- `OPENAI_GUARDRAIL_MODEL`

Transparent optional config in `.env.example`:

- `OPENAI_GUARDRAIL_TEMPERATURE`
- `OPENAI_GUARDRAIL_MAX_TOKENS`
- `OPENAI_GUARDRAIL_MAX_RETRIES`
- `OPENAI_GUARDRAIL_TIMEOUT_SECONDS`
- `OPENAI_GUARDRAIL_API_BASE`
- `OPENAI_GUARDRAIL_API_VERSION`
- `OPENAI_GUARDRAIL_STRICT`
- `OPENAI_GUARDRAIL_REASONING_EFFORT`

Initial default target:

- `GUARDRAIL_PROVIDER="openai"`
- `OPENAI_GUARDRAIL_MODEL="gpt-5-nano"`

Recommended default behavior for classification/rewrite guardrail calls:

- `temperature=0`
- structured output enabled
- `reasoning_effort` optional and unset by default

### Guard-specific settings that still remain

Keep guard-specific env settings only for:

- enable/disable flags
- thresholds
- prompts
- user-facing messages
- special guard behavior flags

This keeps configuration explicit but avoids duplicating provider config for every guard.

## Required New Architecture

Create a new package:

- `src/customer_bot/guardrails/`

Planned files:

- `src/customer_bot/guardrails/__init__.py`
- `src/customer_bot/guardrails/models.py`
- `src/customer_bot/guardrails/service.py`
- `src/customer_bot/guardrails/input.py`
- `src/customer_bot/guardrails/output.py`
- `src/customer_bot/guardrails/rewrite.py`
- `src/customer_bot/guardrails/sanitization.py`
- `src/customer_bot/guardrails/tracing.py`
- `src/customer_bot/guardrails/validators/__init__.py`
- `src/customer_bot/guardrails/validators/secret_pii.py`
- `src/customer_bot/guardrails/validators/prompt_injection.py`
- `src/customer_bot/guardrails/validators/topic_relevance.py`
- `src/customer_bot/guardrails/validators/escalation.py`
- `src/customer_bot/guardrails/validators/grounding.py`
- `src/customer_bot/guardrails/validators/bias.py`

### Responsibilities

#### `models.py`

Define structured internal types for:

- chat status
- guard categories
- guard decisions
- guard results
- pipeline result
- rewrite result
- structured outputs for LLM-based guards

Use explicit typed models.
Prefer Pydantic models if they are part of parsing structured outputs.

#### `service.py`

`GuardrailService` orchestrates:

- running input guards
- running output guards
- evaluating priority rules
- returning structured results to the chat service

It should not own memory writes or API response serialization.

#### `input.py`

Owns:

- input `SecretPII` first-pass
- parallel execution of remaining input guards
- merge/prioritization of final input decision

#### `output.py`

Owns:

- output `SensitiveData` first-pass
- parallel execution of remaining output guards
- merge of final output decision

#### `rewrite.py`

Owns:

- single rewrite call
- no tool use
- same evidence only
- strict structured output if useful for rewrite request/response shape

#### `sanitization.py`

Centralize:

- content masking
- secret pattern replacement
- Langfuse masking logic
- “sanitize before trace” helper functions

#### `tracing.py`

Create helper utilities to produce:

- `input_guardrails` span
- per-input-guard child spans
- per-LLM-guard generation child spans
- `output_guardrails` span
- per-output-guard child spans
- rewrite span/generation

These spans must live under the main request trace.

## Required Changes to Existing Components

### `src/customer_bot/chat/service.py`

Refactor `ChatService` from a simple pass-through into the main pipeline orchestrator.

New responsibilities:

- resolve/generate `session_id`
- load history
- sanitize request content for tracing
- call input guardrail pipeline
- return early on `blocked` or `handoff`
- call agent only on allow
- call output guardrail pipeline
- call rewrite step once if needed
- save only approved/safe final content to memory
- return richer `ChatResult`

Update protocol dependencies accordingly.

### `src/customer_bot/agent/service.py`

Change agent return shape from plain `str` to structured result.

Required information from agent result:

- final answer
- compact tool call summary
- whether tools errored
- whether no-match occurred
- retrieval/tool evidence summary usable by `GroundingGuard`
- whether answer was derived only from prior grounded history

Do not remove current no-match / error fallback behavior.
Preserve current agent tracing behavior and extend it as needed.

### `src/customer_bot/api/models.py`

Extend `ChatResponse` to include:

- `answer: str`
- `session_id: str`
- `status: Literal["answered", "blocked", "handoff", "fallback"]`
- `guardrail_reason: str | None`
- `handoff_required: bool`
- `retry_used: bool`
- `sanitized: bool`

Keep request model contract the same unless absolutely necessary.

### `src/customer_bot/api/routes.py`

Map richer `ChatResult` to the richer `ChatResponse`.

HTTP status remains `200` for chat outcomes.

### `src/customer_bot/api/deps.py`

Add dependency construction for:

- `GuardrailService`
- shared guardrail model client/factory

Keep current dependency cache pattern.

### `src/customer_bot/config.py`

Add:

- `guardrail_provider`
- central `openai_guardrail_*` settings
- per-guard enable/threshold/prompt/message settings
- guardrail tracing settings
- user-facing block/handoff/fallback texts

All of these must be reflected in `.env.example`.

### `src/customer_bot/observability.py`

Update Langfuse initialization to provide `mask=...` using a sanitizer from `guardrails/sanitization.py`.

Important:

- do not blanket-mask every metadata value
- do not hide `session_id`
- do not hide `request_id`
- do not hide status fields
- do not hide non-sensitive config snapshots

Mask only:

- free-text content fields
- sensitive key values
- PII/secret pattern hits

## Guard Definitions

### 1. `SecretPIIGuard`

Purpose:

- block sensitive user input before any downstream LLM/classifier/agent call

Implementation:

- use Hub `DetectPII`
- extend with custom secret/token/key regex heuristics

Config:

- `GUARDRAILS_INPUT_PII_ENABLED`
- `GUARDRAILS_INPUT_PII_ENTITIES`
- `GUARDRAILS_INPUT_PII_CUSTOM_PATTERNS`
- `GUARDRAILS_INPUT_PII_MESSAGE`

Policy:

- `blocked`

### 2. `PromptInjectionGuard`

Purpose:

- block prompt injection or jailbreak-like user messages

Implementation:

- LLM-based classifier using `GUARDRAIL_PROVIDER`
- strict structured output

Config:

- `GUARDRAILS_PROMPT_INJECTION_ENABLED`
- `GUARDRAILS_PROMPT_INJECTION_THRESHOLD`
- `GUARDRAILS_PROMPT_INJECTION_SYSTEM_PROMPT`
- `GUARDRAILS_PROMPT_INJECTION_USER_PROMPT_TEMPLATE`
- `GUARDRAILS_PROMPT_INJECTION_MESSAGE`

Output schema:

- `decision: "allow" | "block"`
- `score: float`
- `reason: str`
- `rewrite_hint: str | None`

Policy:

- `blocked`

### 3. `TopicRelevanceGuard`

Purpose:

- block requests outside FAQ/support scope

Implementation:

- LLM-based classifier using user message plus compact history context
- strict structured output

Config:

- `GUARDRAILS_TOPIC_RELEVANCE_ENABLED`
- `GUARDRAILS_TOPIC_RELEVANCE_THRESHOLD`
- `GUARDRAILS_TOPIC_RELEVANCE_SYSTEM_PROMPT`
- `GUARDRAILS_TOPIC_RELEVANCE_USER_PROMPT_TEMPLATE`
- `GUARDRAILS_TOPIC_RELEVANCE_MESSAGE`
- `GUARDRAILS_TOPIC_RELEVANCE_HELP_TEXT`

Output schema:

- `decision: "allow" | "block"`
- `score: float`
- `reason: str`
- `rewrite_hint: str | None`

Policy:

- `blocked`
- append configurable help text

### 4. `EscalationGuard`

Purpose:

- detect cases that should stop bot handling and hand off to human

Implementation:

- custom rule-based and optionally LLM-assisted classifier
- use compact chat history and current user message

Config:

- `GUARDRAILS_ESCALATION_ENABLED`
- `GUARDRAILS_ESCALATION_THRESHOLD`
- `GUARDRAILS_ESCALATION_SYSTEM_PROMPT`
- `GUARDRAILS_ESCALATION_USER_PROMPT_TEMPLATE`
- `GUARDRAILS_ESCALATION_MESSAGE`

Output schema:

- `decision: "allow" | "handoff"`
- `score: float`
- `reason: str`

Policy:

- `handoff`
- `handoff_required=true`
- no further action hints in v1

### 5. `OutputSensitiveDataGuard`

Purpose:

- prevent sensitive data from being returned to frontend or stored in traces/memory

Implementation:

- reuse the same PII/secret detection family as input

Config:

- `GUARDRAILS_OUTPUT_PII_ENABLED`
- `GUARDRAILS_OUTPUT_PII_ENTITIES`
- `GUARDRAILS_OUTPUT_PII_CUSTOM_PATTERNS`

Policy:

- trigger rewrite once
- fallback if still failing

### 6. `GroundingGuard`

Purpose:

- combine hallucination + relevance verification into one output guard

Implementation:

- LLM-based structured classifier
- compare answer against compact retrieval/tool evidence and grounded history

Config:

- `GUARDRAILS_GROUNDING_ENABLED`
- `GUARDRAILS_GROUNDING_THRESHOLD`
- `GUARDRAILS_GROUNDING_SYSTEM_PROMPT`
- `GUARDRAILS_GROUNDING_USER_PROMPT_TEMPLATE`

Output schema:

- `decision: "allow" | "rewrite" | "fallback"`
- `score: float`
- `reason: str`
- `rewrite_hint: str`

Policy:

- rewrite once, then fallback

### 7. `BiasGuard`

Purpose:

- detect biased or unfair generated output

Implementation:

- LLM-based structured classifier

Config:

- `GUARDRAILS_BIAS_ENABLED`
- `GUARDRAILS_BIAS_THRESHOLD`
- `GUARDRAILS_BIAS_SYSTEM_PROMPT`
- `GUARDRAILS_BIAS_USER_PROMPT_TEMPLATE`

Output schema:

- `decision: "allow" | "rewrite" | "fallback"`
- `score: float`
- `reason: str`
- `rewrite_hint: str`

Policy:

- rewrite once, then fallback

## Langfuse and Masking Rules

### Required trace structure

Every request trace should expose:

- input guards
- agent execution
- output guards
- rewrite step if used

Suggested structure:

- root observation: `chat_request`
- child span: `input_guardrails`
- child span per input guard
- generation child for each LLM-based input guard call
- child span: `agent_execution`
- existing OpenInference/LlamaIndex spans inside agent execution
- child span: `output_guardrails`
- child span per output guard
- generation child for each LLM-based output guard call
- child span/generation: `output_rewrite`

### Langfuse masking requirements

The Langfuse `mask` function must be selective, not blind.

Do not mask these keys/values by default:

- `session_id`
- `request_id`
- `status`
- `guardrail_reason`
- `handoff_required`
- `retry_used`
- `tool_name`
- `faq_id`
- numerical scores
- thresholds
- non-secret config metadata

Do mask:

- `input`
- `output`
- `messages`
- `content`
- `user_message`
- `assistant_message`
- keys like:
  - `authorization`
  - `api_key`
  - `token`
  - `secret`
  - `password`

Also mask any values matched by PII/secret patterns.

Implementation note:

- create a recursive path-aware masking function
- use field name / path checks, not only regex
- sanitize app-level payloads before tracing and also pass the Langfuse `mask` callback as a second layer

## Required Config Additions

Add to `Settings`, `.env.example`, and `README.md`.

### Global guardrail config

- `GUARDRAILS_ENABLED`
- `GUARDRAILS_FAIL_CLOSED`
- `GUARDRAILS_MAX_OUTPUT_RETRIES`
- `GUARDRAILS_TRACE_INPUTS`
- `GUARDRAILS_TRACE_OUTPUTS`
- `GUARDRAILS_TRACE_INCLUDE_CONFIG`
- `GUARDRAILS_TRACE_INCLUDE_SCORES`

### Provider/model config

- `GUARDRAIL_PROVIDER`
- `OPENAI_GUARDRAIL_MODEL`
- `OPENAI_GUARDRAIL_TEMPERATURE`
- `OPENAI_GUARDRAIL_MAX_TOKENS`
- `OPENAI_GUARDRAIL_MAX_RETRIES`
- `OPENAI_GUARDRAIL_TIMEOUT_SECONDS`
- `OPENAI_GUARDRAIL_API_BASE`
- `OPENAI_GUARDRAIL_API_VERSION`
- `OPENAI_GUARDRAIL_STRICT`
- `OPENAI_GUARDRAIL_REASONING_EFFORT`

### Input PII

- `GUARDRAILS_INPUT_PII_ENABLED`
- `GUARDRAILS_INPUT_PII_ENTITIES`
- `GUARDRAILS_INPUT_PII_CUSTOM_PATTERNS`
- `GUARDRAILS_INPUT_PII_MESSAGE`

### Prompt injection

- `GUARDRAILS_PROMPT_INJECTION_ENABLED`
- `GUARDRAILS_PROMPT_INJECTION_THRESHOLD`
- `GUARDRAILS_PROMPT_INJECTION_SYSTEM_PROMPT`
- `GUARDRAILS_PROMPT_INJECTION_USER_PROMPT_TEMPLATE`
- `GUARDRAILS_PROMPT_INJECTION_MESSAGE`

### Topic relevance

- `GUARDRAILS_TOPIC_RELEVANCE_ENABLED`
- `GUARDRAILS_TOPIC_RELEVANCE_THRESHOLD`
- `GUARDRAILS_TOPIC_RELEVANCE_SYSTEM_PROMPT`
- `GUARDRAILS_TOPIC_RELEVANCE_USER_PROMPT_TEMPLATE`
- `GUARDRAILS_TOPIC_RELEVANCE_MESSAGE`
- `GUARDRAILS_TOPIC_RELEVANCE_HELP_TEXT`

### Escalation

- `GUARDRAILS_ESCALATION_ENABLED`
- `GUARDRAILS_ESCALATION_THRESHOLD`
- `GUARDRAILS_ESCALATION_SYSTEM_PROMPT`
- `GUARDRAILS_ESCALATION_USER_PROMPT_TEMPLATE`
- `GUARDRAILS_ESCALATION_MESSAGE`

### Output PII

- `GUARDRAILS_OUTPUT_PII_ENABLED`
- `GUARDRAILS_OUTPUT_PII_ENTITIES`
- `GUARDRAILS_OUTPUT_PII_CUSTOM_PATTERNS`

### Grounding

- `GUARDRAILS_GROUNDING_ENABLED`
- `GUARDRAILS_GROUNDING_THRESHOLD`
- `GUARDRAILS_GROUNDING_SYSTEM_PROMPT`
- `GUARDRAILS_GROUNDING_USER_PROMPT_TEMPLATE`

### Bias

- `GUARDRAILS_BIAS_ENABLED`
- `GUARDRAILS_BIAS_THRESHOLD`
- `GUARDRAILS_BIAS_SYSTEM_PROMPT`
- `GUARDRAILS_BIAS_USER_PROMPT_TEMPLATE`

### Rewrite

- `GUARDRAILS_REWRITE_ENABLED`
- `GUARDRAILS_REWRITE_SYSTEM_PROMPT`
- `GUARDRAILS_REWRITE_USER_PROMPT_TEMPLATE`

### User-facing texts

Keep visible frontend texts explicitly configurable in env.

## Suggested Implementation Order

1. Add config model fields in `src/customer_bot/config.py`
2. Update `.env.example` with full documented config
3. Update `README.md` with new runtime behavior and response contract
4. Add guardrail internal models and package skeleton
5. Add central guardrail OpenAI client/factory
6. Add sanitization and Langfuse mask helper
7. Update `observability.py` to use mask callback
8. Extend API response model and chat result model
9. Refactor `AgentService` to return structured result
10. Implement input pipeline and input guards
11. Implement output pipeline and output guards
12. Implement rewrite step
13. Refactor `ChatService` orchestration
14. Wire dependencies
15. Add/adjust tests
16. Run quality gates

## Test Plan

### Unit tests

Add or update tests for:

- `ChatService`
  - blocked input
  - handoff input
  - answered flow
  - fallback flow
  - memory write policy
- `AgentService`
  - structured result return shape
  - no-match and error fallback preserved
- API route tests
  - response model includes new fields
- Guardrail service/pipelines
  - input PII first
  - output PII first
  - input priority behavior
  - rewrite exactly once
  - fail-closed handling
- Sanitization/masking
  - `session_id` not masked
  - `request_id` not masked
  - content fields masked
  - secret-like keys masked
- Structured output parsing
  - invalid output fails cleanly

### Integration/regression tests

At minimum:

- chat request still works end-to-end for normal FAQ case
- no-match behavior preserved
- technical fallback behavior preserved
- session isolation preserved
- tracing-related code does not break startup

## Verification Commands

For implementation work touching code/config/tests, follow repo guidance:

- `uv run ruff check --fix .`
- `uv run ruff format .`
- `uv run ty check src --output-format concise`
- `uv run pytest --collect-only`
- `uv run pytest -m unit`
- then smallest relevant broader subset depending on touched scope

If blocked by missing services/dependencies, report the exact blocked command.

## Dependencies and Docs to Check During Implementation

### Local files

- `AGENTS.md`
- `README.md`
- `.env.example`
- `src/customer_bot/chat/service.py`
- `src/customer_bot/agent/service.py`
- `src/customer_bot/api/models.py`
- `src/customer_bot/api/routes.py`
- `src/customer_bot/api/deps.py`
- `src/customer_bot/config.py`
- `src/customer_bot/observability.py`
- `src/customer_bot/agent/tracing.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_api_routes.py`
- `tests/unit/test_agent_service.py`

### Local planning/reference docs

- `PLAN.md`
- `GUARDRAILS_AI_DOCS.md`
- `GUARDRAILS_AI_IN_HUB.md`

## Non-Goals for v1

Do not add in v1:

- separate Guardrails Server deployment
- frontend-specific action suggestions beyond `handoff_required`
- multi-provider guardrail support beyond `GUARDRAIL_PROVIDER=openai`
- full agent reruns as retry strategy
- hidden runtime defaults not reflected in docs/config

## Definition of Done

The work is done when:

1. Input and output guardrails are implemented with the fixed flow described here
2. `POST /chat` exposes the new response contract
3. Memory policy matches this plan exactly
4. Agent no-match/error invariants remain intact
5. Langfuse shows input guards, agent traces, output guards, and rewrite traces with masked content but visible operational metadata
6. All new runtime/config behavior is documented in `README.md` and `.env.example`
7. Relevant tests and quality checks were run, or blockers were reported exactly
