# AGENTS.md

## Mission
Build and ship a reliable FastAPI + LlamaIndex customer support agent with reproducible workflows, explicit contracts, clear observability, and strict quality gates.

## Repo Landmarks
- `src/customer_bot/`: backend application code
- `src/customer_bot/config/defaults/`: versioned YAML defaults for runtime behavior
- `frontend/`: separate React/Vite frontend shell
- `dataset/`: FAQ and product corpora, defaulting to `dataset/corpus.csv` and `dataset/products.csv`
- `tests/`: unit and integration tests
- `pyproject.toml`: scripts, dependencies, pytest markers, and tooling config
- `README.md`: user-facing runtime, API, guardrail, and troubleshooting guide
- `.env.example`: current secret and runtime override surface

## Working Agreement For Agents
- Read the relevant code and docs first, then make the smallest useful change.
- Treat `README.md`, `.env.example`, `pyproject.toml`, and `src/customer_bot/config/defaults/` as the primary sources of truth for runtime behavior.
- Plan first for ambiguous, risky, or architecture-shaping work.
- Preserve existing FastAPI, LlamaIndex, guardrail, tracing, and test patterns unless the task explicitly requires a refactor.
- Keep scope explicit. If a change affects contracts, config, workflows, or architecture expectations, update the matching docs in the same pass.
- Prefer explicit configuration and explicit failure over hidden defaults.
- In reviews, prioritize bugs, regressions, broken contracts, stale docs, and missing tests.
- If Codex makes the same mistake twice, update `AGENTS.md` so the guidance becomes durable.

## Current Contracts
- CLI entrypoints:
  - `customer-bot`
  - `customer-bot-api`
  - `customer-bot-ingest`
- HTTP API:
  - `GET /health` returns `{"status":"ok"}`
  - `POST /chat` requires `user_message` and accepts optional `session_id`
  - `/chat` returns structured metadata including `status`, `guardrail_reason`, `handoff_required`, `retry_used`, `sanitized`, and `trace_id` when tracing is configured
- Data:
  - FAQ CSV requires `faq_id`, `question`, `answer`
  - product CSV requires `product_id`, `name`, `description`
  - FAQ and product ingestion stay separate and deterministic
  - `INGESTION__FAQ__TEXT_INGESTION_MODE` only allows `question_only`, `answer_only`, `question_answer`
- Providers:
  - supported LLM providers: `ollama`, `openai`
  - supported embedding providers: `ollama`, `openai`
  - supported guardrail provider: `openai`
- Guardrails:
  - input guardrails cover PII/secret checks, prompt injection, topic relevance, and escalation
  - output guardrails cover output-sensitive-data, grounding, bias, and rewrite/fallback behavior
- Observability:
  - LlamaIndex tracing uses OpenInference instrumentation as the baseline
  - Langfuse is explicit and optional

## Documentation Standard
- Write code so a new engineer, or future you after a year away from the repo, can recover intent quickly.
- Use English for docstrings and code comments.
- Document heavily:
  - services
  - pipelines
  - factories and provider wiring
  - tracing and observability helpers
  - ingestion and validation logic
  - config loading and compatibility logic
  - policy-heavy guardrail code
- Document lightly:
  - simple data containers
  - obvious request/response models
  - tiny adapters
  - package `__init__.py` re-export files
- Module docstrings belong on non-trivial modules.
- Class and function docstrings should explain responsibility, contract, and important invariants.
- Comments should explain invariants, ordering, tradeoffs, security/privacy rationale, or failure modes.
- Do not narrate obvious line-by-line behavior.
- In tests, prefer descriptive names and clean arrange/act/assert structure over explanatory comments.

## Git & PR Workflow
- Never push directly to `main`.
- For every code, docs, or config change, create a new branch from current `main` first.
- Use branch prefixes: `feat/*`, `fix/*`, `docs/*`, `chore/*`.
- Commit incrementally on the branch until the task is ready.
- Before opening a PR, run the smallest relevant checks from the Verification Matrix for the touched scope.
- Open a PR only when the user explicitly asks.

## Verification Matrix
- After code edits, run:
  - `uv run ruff check --fix .`
  - `uv run ruff format .`
  - `uv run ty check src --output-format concise`
- For documentation-only changes, manually verify consistency against `README.md`, `.env.example`, `pyproject.toml`, and the current code.
- For unit-scale logic or test changes, run:
  - `uv run pytest --collect-only`
  - `uv run pytest -m unit`
- For API, retrieval, ingest, config, guardrail, observability, or memory changes, run `uv run pytest --collect-only` plus the smallest relevant pytest subset first.
- For broader backend changes, run `uv run pytest -m "not slow and not network"`.
- For integration changes, run `uv run pytest -m "integration and not network"`.
- For network-dependent integrations, run `uv run pytest -m "integration and network"`.
- For frontend changes, run `cd frontend && npm run build`.
- Keep global `DeprecationWarning` strict in pytest config.

## Project-Specific Risk Checks
- Retrieval and agent changes must preserve no-match behavior and safe fallback behavior.
- Ingestion changes must preserve schema validation, deterministic rebuild semantics, and separate FAQ/product collection behavior.
- Memory changes must preserve session isolation, bounded history, and current redaction behavior.
- Guardrail changes must preserve the current input/output pipeline structure unless the task explicitly changes policy.
- Config and provider changes must stay synchronized across code, `README.md`, `.env.example`, and defaults YAML where relevant.
- Provider wiring must keep required keys explicit and fail clearly during startup or runtime wiring.
- Observability changes must keep tracing explicit and surface startup/auth/connectivity failure modes clearly.
- Documentation changes must not drift away from the actual code or current runtime behavior.

## Do-Not Rules
- Do not run destructive git commands such as `git reset --hard` unless explicitly requested.
- Do not push commits directly to `main`.
- Do not commit secrets, tokens, or local credential files.
- Do not manage Python dependencies outside `uv`.
- Do not introduce hidden runtime defaults that are not reflected in code and the relevant docs.
- Do not update `AGENTS.md` with behavior the codebase does not actually implement.

## Failure Handling
- Report the failing stage and exact error details, including the command and the relevant exception or message.
- If checks cannot run because of missing services, credentials, or external dependencies, say so explicitly and list the blocked command.
- Prefer the smallest reproducible failing command before escalating to broader retries.
- If repo docs and code disagree, treat the code and config as the deciding source first, then bring the docs back into sync.

## Definition of Done
1. Changed scope is implemented and consistent with current contracts.
2. Relevant verification was run for the touched scope, or blockers were stated explicitly.
3. Relevant pytest commands were run for the touched scope, or blockers were stated explicitly.
4. No obvious regressions remain in touched areas.
5. Documentation and config contracts remain synchronized with current behavior.
6. If runtime or config behavior changed, update `.env.example`, `README.md`, defaults YAML, and code as needed.
7. Documentation changes follow the repository documentation standard instead of adding comment noise.
8. For branch-based work, changes are on a non-`main` branch and a PR is opened only after explicit user instruction.

## References
- `README.md`: runtime setup, API examples, guardrails, observability, troubleshooting
- `.env.example`: current environment keys and runtime override surface
- `CODEX_BEST_PRACTICES.md`: prompting, planning, durable agent guidance, and workflow design
- `GH_CLI_BEST_PRACTICES.md`: practical `git` + GitHub CLI workflow
- `PYTEST_BEST_PRACTICES.md`: test architecture, fixtures, markers, and warning policy
- `LLAMAINDEX_BEST_PRACTICES.md`: retrieval, memory, observability, and integration guidance
