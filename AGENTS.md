# AGENTS.md

## Mission
Build and ship a reliable FastAPI + LlamaIndex Customer Support Agent with reproducible local workflows, clear contracts, and strict quality gates.

## Repo Landmarks
- `src/`: application code
- `dataset/`: FAQ corpus, default `dataset/corpus.csv`
- `tests/`: unit and integration tests
- `pyproject.toml`: scripts, dependencies, pytest markers, tooling config
- `README.md`: setup, run, ingest, API usage, troubleshooting
- `.env.example`: current env keys and defaults

## Working Agreement For Agents
- Read the relevant code and docs first, then make the smallest useful change.
- Preserve existing FastAPI, LlamaIndex, and test patterns unless the task requires a refactor.
- Treat `README.md` and `.env.example` as the source of truth for runtime setup and config.
- Plan first for multi-step, ambiguous, or architecture-shaping work.
- Keep scope explicit. If a change affects contracts, config, or workflows, update the matching docs.
- In reviews, prioritize bugs, regressions, broken contracts, and missing tests.

## Git & PR Workflow (Simple)
- Never push directly to `main`.
- For every code/docs/config change, create a new branch from current `main` first.
- Use branch prefixes: `feat/*`, `fix/*`, `docs/*`, `chore/*`.
- Commit incrementally on the branch until the task is ready.
- Before opening a PR, run the smallest relevant checks from the Verification Matrix for the touched scope.
- Open a PR only when the user explicitly asks (for example: "open PR", "create PR").
- If no explicit PR instruction exists, keep working on the branch and do not open a PR.

## Project Invariants
- API:
  - `POST /chat` requires `user_message` and accepts optional `session_id`
  - `GET /health` returns service health status
- Data:
  - default corpus path is `dataset/corpus.csv`
  - required CSV columns are `faq_id`, `question`, `answer`
  - `TEXT_INGESTION_MODE` only allows `question_only`, `answer_only`, `question_answer`
- Behavior:
  - retrieval-backed answers must preserve explicit no-match and error fallback behavior
  - session memory is isolated by `session_id`
  - ingestion remains deterministic and avoids uncontrolled duplication on rebuild
  - LLM and embedding provider selection is explicit via env config and must stay validated
  - OpenRouter is supported for LLM only; embedding providers remain `ollama`, `openai`, `gemini`
- Observability:
  - LlamaIndex tracing uses OpenInference instrumentation as the baseline
  - Langfuse configuration is explicit and optional, not hidden by silent defaults

## Verification Matrix
- After code edits, run `uv run ruff check --fix .` and `uv run ruff format .`.
- Run blocking type checks with `uv run ty check src --output-format concise`.
- For documentation-only changes, manually verify consistency against `README.md`, `.env.example`, and `pyproject.toml`.
- For unit-scale logic or test changes, run `uv run pytest --collect-only` and `uv run pytest -m unit`.
- For API, retrieval, ingest, config, or memory changes, run `uv run pytest --collect-only` plus the smallest relevant pytest subset first.
- For broader or cross-cutting changes, run `uv run pytest -m "not slow and not network"`.
- For integration changes, run `uv run pytest -m "integration and not network"`.
- For network-dependent integrations, additionally run `uv run pytest -m "integration and network"`.
- Keep global `DeprecationWarning` strict in pytest config.
- If a third-party deprecation must be tolerated in tests, use targeted `@pytest.mark.filterwarnings(...)` on the affected test only.

## Project-Specific Risk Checks
- Retrieval and agent changes must preserve no-match and safe fallback behavior.
- Memory changes must preserve session isolation and bounded history behavior.
- Ingestion changes must keep schema validation and deterministic rebuild semantics.
- Config changes must stay synchronized across code, `README.md`, and `.env.example`.
- Provider changes must keep required API keys explicit and fail clearly on startup/runtime wiring.
- Observability changes must keep tracing explicit and must surface startup failure modes clearly.

## Do-Not Rules
- Do not run destructive git commands (for example `git reset --hard`) unless explicitly requested.
- Do not push commits directly to `main`; always use branch + PR workflow.
- Do not commit secrets, tokens, or local credential files.
- Do not manage dependencies outside `uv`.
- Do not introduce hidden runtime defaults that are not reflected in `README.md`, `.env.example`, and the code.

## Failure Handling
- Report failing stage and exact error details (command, exception/message).
- If tests cannot run due missing services/dependencies, state it clearly and list the blocked command.
- Prefer smallest reproducible failing command before attempting broad retries.

## Definition of Done
1. Changed scope is implemented and consistent with contracts.
2. Relevant verification was run for the touched scope, or blockers were stated explicitly.
3. Relevant pytest commands were run for touched scope (or blockers explicitly stated).
4. No obvious regressions in touched areas.
5. Documentation/config contracts remain synchronized with behavior changes.
6. If runtime/config behavior changed, `.env.example` and contract docs were updated accordingly.
7. For branch-based work, changes are on a non-`main` branch and PR is opened only after explicit user instruction and required checks.

## References
- `README.md`: runtime setup, API examples, troubleshooting, config overview
- `.env.example`: current environment keys and default values
- `CODEX_BEST_PRACTICES.md`: prompting, planning, reviews, skills, automations
- `GH_CLI_BEST_PRACTICES.md`: practical `git` + GitHub CLI workflow for branch/PR/review/merge/worktree operations
- `PYTEST_BEST_PRACTICES.md`: test architecture, fixtures, markers, warning policy
- `LLAMAINDEX_BEST_PRACTICES.md`: retrieval, memory, observability, and integration guidance
