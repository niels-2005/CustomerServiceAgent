# AGENTS.md

## Mission
Build and ship a reliable FastAPI + LlamaIndex Customer Support Agent with reproducible local workflows, clear contracts, and strict quality gates.

## Repo Landmarks
- `src/`: application code
- `dataset/`: FAQ corpus inputs (default `dataset/corpus.csv`)
- `tests/`: test suite (unit/integration, when present)
- `pyproject.toml`: dependency + tooling source of truth

## Essential Commands
- Sync dependencies: `uv sync`
- Start API: `uv run customer-bot-api`
- Ingest FAQ corpus: `uv run customer-bot-ingest`
- Show ingest CLI help: `uv run customer-bot-ingest --help`
- Lint/fix: `uv run ruff check --fix .`
- Format: `uv run ruff format .`
- Pytest collect sanity: `uv run pytest --collect-only`
- Default test loop: `uv run pytest -m "not slow and not network"`
- Integration loop (offline): `uv run pytest -m "integration and not network"`
- Optional network integration: `uv run pytest -m "integration and network"`

## Contracts
- API contract:
  - `POST /chat`: `user_message` required, `session_id` optional
  - `GET /health`: returns service health status
- Data contract:
  - corpus CSV default path: `dataset/corpus.csv`
  - required columns: `faq_id`, `question`, `answer`
- Observability contract:
  - LlamaIndex tracing enabled via OpenInference instrumentation
  - Langfuse env keys use: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`

## Verification Rules
- Always after edits:
  - `uv run ruff check --fix .`
  - `uv run ruff format .`
- For API, retrieval, ingest, config, or memory changes:
  - `uv run pytest --collect-only`
  - run relevant targeted pytest subset
- For broader cross-cutting changes:
  - `uv run pytest -m "not slow and not network"`
- For integration-specific changes:
  - `uv run pytest -m "integration and not network"`
- For network integration changes:
  - additionally `uv run pytest -m "integration and network"`

## Do-Not Rules
- Do not run destructive git commands (for example `git reset --hard`) unless explicitly requested.
- Do not commit secrets, tokens, or local credential files.
- Do not manage dependencies outside `uv`.
- Do not introduce hidden runtime defaults that are not reflected in config/contracts.

## Failure Handling
- Report failing stage and exact error details (command, exception/message).
- If tests cannot run due missing services/dependencies, state it clearly and list the blocked command.
- Prefer smallest reproducible failing command before attempting broad retries.

## Definition of Done
1. Changed scope is implemented and consistent with contracts.
2. Ruff check/format were run after edits.
3. Relevant pytest commands were run for touched scope (or blockers explicitly stated).
4. No obvious regressions in touched areas.
5. Documentation/config contracts remain synchronized with behavior changes.

## References
- `CODEX_BEST_PRACTICES.md`
- `PYTEST_BEST_PRACTICES.md`
- `LLAMAINDEX_BEST_PRACTICES.md`
