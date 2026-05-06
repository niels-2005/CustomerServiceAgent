## Mission
Maintain a reliable FastAPI + LlamaIndex customer support agent with explicit runtime config, reproducible validation, and safe, testable behavior.

## Repo Landmarks
- `src/customer_bot/`: backend app, API, agent, retrieval, guardrails, memory, observability
- `src/customer_bot/config/defaults/`: versioned YAML runtime defaults
- `frontend/`: React/Vite frontend
- `datasets/rag/`: FAQ and product corpora used for ingestion
- `datasets/benchmark/`: DeepEval benchmark datasets and golden cases
- `tests/unit/`: deterministic unit tests
- `tests/integration/`: multi-component backend tests
- `tests/evals/`: DeepEval end-to-end eval suites and Langfuse bridge helpers
- `pyproject.toml`: dependencies, scripts, pytest markers, tool config
- `README.md`: user-facing project documentation, useful but not guaranteed current
- `.env.example`: example env surface, update only on explicit request

## Working Agreement
- Read the relevant code and docs first, then make the smallest useful change.
- Treat code, tests, `pyproject.toml`, and `src/customer_bot/config/defaults/` as the primary source of truth.
- Treat `README.md` and `.env.example` as supporting docs, not authoritative runtime truth.
- Plan first for ambiguous, risky, or architecture-shaping work.
- Preserve existing FastAPI, LlamaIndex, guardrail, tracing, eval, and test patterns unless the task explicitly requires a refactor.
- Prefer explicit configuration and explicit failure over hidden defaults.
- If code changes affect documented behavior, call out any `README.md` or `.env.example` drift in the final response unless the user explicitly asked to update those files.
- Only edit `README.md` or `.env.example` when the user explicitly asks.
- In reviews, prioritize bugs, regressions, broken contracts, stale docs, and missing tests.

## Stable Interfaces
- CLI entrypoints:
  - `customer-bot`
  - `customer-bot-api`
  - `customer-bot-ingest`
- HTTP API:
  - `GET /health` returns `{"status":"ok"}`
  - `POST /chat` requires `user_message` and accepts optional `session_id`
  - `/chat` returns `answer`, `session_id`, `handoff_required`, optional `trace_id`, and `meta`
  - `meta.status` is one of `answered`, `blocked`, `handoff`, `fallback`, `session_limit`
  - `meta` includes `guardrail_reason`, `retry_used`, and `sanitized`
- Data and retrieval:
  - FAQ and product ingestion stay separate and deterministic
  - `INGESTION__FAQ__TEXT_INGESTION_MODE` only allows `question_only`, `answer_only`, `question_answer`
  - retrieval prefetch is part of the chat execution path and observability surface
- Providers:
  - supported LLM providers: `ollama`, `openai`
  - supported embedding providers: `ollama`, `openai`
  - supported guardrail provider: `openai`
- Observability:
  - tracing is explicit
  - Langfuse is optional and configuration-driven

## Documentation Standard
- Use English for docstrings and comments.
- Document non-trivial modules, services, pipelines, provider/config wiring, tracing helpers, ingestion logic, and policy-heavy guardrail code.
- Keep simple models, tiny adapters, and obvious glue code lightly documented.
- Comments should explain contracts, invariants, tradeoffs, ordering, or failure modes, not obvious line-by-line behavior.
- In tests, prefer descriptive names and clear arrange/act/assert structure.

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
- For documentation-only changes, manually verify consistency against current code, config defaults, and `pyproject.toml`.
- For unit-scale logic or test changes, run:
  - `uv run pytest --collect-only`
  - `uv run pytest -m unit`
- For API, retrieval, ingest, config, guardrail, observability, memory, or agent changes, run `uv run pytest --collect-only` plus the smallest relevant pytest subset first.
- For broader backend changes, run `uv run pytest -m "not slow and not network"`.
- For integration changes, run `uv run pytest -m "integration and not network"`.
- For network-dependent integrations, run `uv run pytest -m "integration and network"`.
- For eval changes, run:
  - `uv run pytest --collect-only`
  - `DEEPEVAL_DISABLE_DOTENV=1 uv run deepeval test run tests/evals -m "eval_deterministic"`
  - `DEEPEVAL_DISABLE_DOTENV=1 uv run deepeval test run tests/evals -m "eval_llm_judge"`
- For frontend changes, run `cd frontend && npm run build`.
- Keep global `DeprecationWarning` strict in pytest config.

## Project-Specific Risk Checks
- Retrieval and agent changes must preserve no-match behavior, safe fallback behavior, and current tool/evidence semantics.
- Retrieval prefetch changes must preserve traceability and must not silently bypass the agent's safe fallback path.
- Ingestion changes must preserve schema validation, deterministic rebuild semantics, and separate FAQ/product collection behavior.
- Memory changes must preserve session isolation, bounded history, and current redaction behavior.
- Guardrail changes must preserve explicit pipeline ordering and configured fail-closed or fallback behavior.
- Provider wiring must keep required keys explicit and fail clearly during startup or runtime wiring.
- Observability changes must keep tracing explicit and surface startup, auth, or connectivity failures clearly.
- Eval changes must preserve benchmark dataset determinism and Langfuse trace or score linkage where applicable.
- Documentation changes must not drift away from actual code or current runtime behavior.

## Do-Not Rules
- Do not run destructive git commands such as `git reset --hard` unless explicitly requested.
- Do not push commits directly to `main`.
- Do not commit secrets, tokens, or local credential files.
- Do not manage Python dependencies outside `uv`.
- Do not introduce hidden runtime defaults that are not reflected in code and the relevant config defaults.
- Do not update `AGENTS.md` with behavior the codebase does not actually implement.

## Failure Handling
- Report the failing stage and exact error details, including the command and the relevant exception or message.
- If checks cannot run because of missing services, credentials, or external dependencies, say so explicitly and list the blocked command.
- Prefer the smallest reproducible failing command before escalating to broader retries.
- If repo docs and code disagree, treat code and config as the deciding source first, then call out or fix drift as requested.

## Definition of Done
1. Changed scope is implemented and consistent with current code-level contracts.
2. Relevant verification was run for the touched scope, or blockers were stated explicitly.
3. Relevant pytest or eval commands were run for the touched scope, or blockers were stated explicitly.
4. No obvious regressions remain in touched areas.
5. If runtime behavior changed, code and config defaults were updated in the same pass.
6. If user-facing docs or env examples are now stale, they were updated only when explicitly requested or the drift was called out explicitly.
7. Documentation changes follow the repository documentation standard instead of adding comment noise.
8. For branch-based work, changes are on a non-`main` branch and a PR is opened only after explicit user instruction.
