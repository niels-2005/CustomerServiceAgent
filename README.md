# customer-bot

FastAPI + LlamaIndex customer support agent for FAQ and product-style chat.

This project provides a local-first v1 stack:
- FastAPI API (`/health`, `/chat`)
- Separate React/Vite frontend with a premium dark marketing shell and `Frag KI` chat launcher
- CSV ingestion into a pluggable vector backend (default: Chroma)
- Provider-based LLM + embeddings (Ollama, OpenAI)
- Session-scoped short-term memory
- Optional Langfuse tracing via OpenInference
- Request IDs, structured API errors, baseline CORS/trusted-host protection, and rate limiting

## What This Project Is

`customer-bot` is a retrieval-backed support assistant for FAQ and product knowledge workloads.
You ingest CSV corpora, start the API, and send user messages to `/chat`.
The agent retrieves FAQ or product candidates from the configured vector backend (default: Chroma) and returns an answer (or a safe fallback if no good match exists).

## Current v1 Capabilities

- `GET /health` for service health.
- `POST /chat` with:
  - required: `user_message`
  - optional: `session_id`
- CSV ingestion CLI (`customer-bot-ingest`) with per-source schema validation.
- Deterministic full-rebuild ingestion behavior (no uncontrolled duplication).
- Session memory isolation by `session_id`.
- Config-driven text ingestion mode:
  - `question_only`
  - `answer_only`
  - `question_answer`

## Prerequisites

- Python `>=3.11`
- `uv` installed
- Create `.env` from `.env.example` for secrets and optional runtime overrides
- Provider requirements based on your selection:
  - Ollama: local Ollama running and models pulled locally
  - OpenAI: `OPENAI_API_KEY`

## Quickstart (Local)

1. Install dependencies:

```bash
uv sync
```

2. Create local config:

```bash
cp .env.example .env
```

3. Ingest knowledge corpora:

```bash
uv run customer-bot-ingest --source faq
uv run customer-bot-ingest --source products
```

4. Start API:

```bash
uv run customer-bot-api
```

By default, API is available at `http://127.0.0.1:8000`.

## Frontend Quickstart

The repo includes a separate demo frontend in `frontend/`:

1. Install frontend dependencies:

```bash
cd frontend
npm install
```

2. Create local frontend config:

```bash
cp .env.example .env
```

3. Start the frontend:

```bash
cd frontend
npm run dev
```

By default, Vite runs on `http://127.0.0.1:5173`, which is already included in the
backend CORS defaults. The page is intentionally minimal: a premium dark landing
page with a fixed `Frag KI` launcher that opens the chat panel and calls the FastAPI
`/chat` endpoint. The frontend reads its `VITE_*` variables from the repo root `.env`.

## API Usage

### Health check

```bash
curl -s http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

### Chat request

```bash
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"How can I create an account?"}'
```

Response shape:

```json
{
  "answer":"...",
  "session_id":"...",
  "trace_id":"...",
  "status":"answered",
  "guardrail_reason":null,
  "handoff_required":false,
  "retry_used":false,
  "sanitized":false
}
```

Error shape:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed.",
    "details": []
  },
  "request_id": "..."
}
```

All API responses include `X-Request-ID`. Clients may optionally send their own `X-Request-ID`, otherwise the API generates one.

### Reuse the same session

```bash
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"And what if I forgot my password?","session_id":"<SESSION_ID_FROM_PREVIOUS_RESPONSE>"}'
```

### API docs

- Swagger UI: `http://127.0.0.1:8000/docs`

## Configuration

The app now uses a hybrid configuration model:

- YAML files in `src/customer_bot/config/defaults/` are the versioned source of truth for non-secret defaults.
- `.env` is reserved for secrets and a small set of deployment-specific overrides.
- Runtime precedence is: init kwargs > process env / `.env` > YAML defaults.

Default YAML files:

- `api.yaml`: API limits, CORS defaults, trusted hosts, rate limiting
- `providers.yaml`: nested sections for `selectors`, `llm`, `embedding`, and `guardrail`
- `retrieval.yaml`: nested sections for `storage`, `ingestion`, `retrieval`, and `memory`
- `agent.yaml`: grouped `agent` behavior and user-facing `messages`
- `guardrails.yaml`: nested `global`, `tracing`, `input`, and `output` guard sections
- `observability.yaml`: grouped `langfuse` observability defaults
- `defaults/presidio_config.yaml`: Presidio engine recognizer/NLP configuration used by input/output PII checks

Environment variables kept in `.env.example`:

| Group | Keys |
|---|---|
| Secrets | `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` |
| Frontend | `VITE_API_BASE_URL` |
| Optional runtime overrides | `API__HOST`, `API__PORT`, `LLM__OLLAMA__BASE_URL`, `LANGFUSE_HOST`, `STORAGE__CHROMA_PERSIST_DIR`, `INGESTION__FAQ__CORPUS_CSV_PATH`, `INGESTION__PRODUCTS__CORPUS_CSV_PATH`, `STORAGE__FAQ__COLLECTION_NAME`, `STORAGE__PRODUCTS__COLLECTION_NAME`, `RETRIEVAL__FAQ__TOP_K`, `RETRIEVAL__FAQ__SIMILARITY_CUTOFF`, `RETRIEVAL__PRODUCTS__TOP_K`, `RETRIEVAL__PRODUCTS__SIMILARITY_CUTOFF` |

Environment override naming follows the nested settings structure via `__`, for example `API__PORT` -> `settings.api.port`. `LANGFUSE_HOST` remains supported as a compatibility override because the repo root `.env` is also consumed by the frontend.

`INGESTION__FAQ__TEXT_INGESTION_MODE` only accepts:
- `question_only`
- `answer_only`
- `question_answer`

Retrieval behavior:
- FAQ and products each have their own `top_k` and `similarity_cutoff`.
- if fewer matches remain after the configured source-specific cutoff, only those remaining matches are used.

API protection defaults:
- `POST /chat` trims `user_message`, rejects blank input, and caps it via `api.max_user_message_length`.
- `session_id` is optional; blank values are normalized away before the backend decides whether to reuse or generate a session.
- CORS uses an explicit origin allowlist.
- `POST /chat` is rate-limited by `api.chat_rate_limit`.
- `/health` remains a simple liveness endpoint and returns `{"status":"ok"}` after successful startup.

Langfuse trace shape:
- root `input` includes `system_prompt_version`, `user_message`, and `session_id`
- root `output` includes `answer`
- full tool inputs/outputs are additionally captured as nested Langfuse `tool` observations
- `POST /chat` returns `trace_id` when Langfuse tracing is configured so the frontend can attach explicit user feedback to the same trace

Explicit user feedback:
- the frontend renders thumbs up/down under traced assistant messages
- feedback is sent from the browser via the Langfuse Web SDK as a score named `user-thumbs`
- the frontend reuses `LANGFUSE_PUBLIC_KEY` from the root `.env` via an explicit Vite bridge; `LANGFUSE_SECRET_KEY` stays backend-only
- the frontend uses `LANGFUSE_HOST` when set, otherwise Langfuse defaults apply

## Guardrails

When `GUARDRAILS_ENABLED=true`, the `/chat` pipeline becomes:

1. input PII/secret guard
2. prompt-injection, topic, and escalation input guards
3. FAQ agent execution
4. output PII guard
5. grounding and bias output guards
6. one rewrite attempt
7. fallback if the rewritten output still fails

`POST /chat` always returns HTTP `200`, but `status` becomes one of:
- `answered`
- `blocked`
- `handoff`
- `fallback`

`guardrail_reason` is a machine-readable reason such as `secret_pii`, `prompt_injection`, `off_topic`, `escalation`, `output_sensitive_data`, `grounding`, `bias`, or `guardrail_error`.

### Guardrails setup

For input/output PII validation, no Guardrails Hub setup is required. The app uses
Microsoft Presidio directly through the Python dependencies installed by `uv sync`.

```bash
uv sync
uv run python -m spacy download de_core_news_md
```

If `GUARDRAILS_ENABLED=true` and Presidio is unavailable or misconfigured, the PII
guard fails clearly during runtime evaluation.

The bundled Presidio configuration lives at `src/customer_bot/config/defaults/presidio_config.yaml`.
By default, it is configured for German (`guardrails.input.pii.presidio_language: de`) and
detects `EMAIL_ADDRESS`, `PHONE_NUMBER`, `IBAN_CODE`, `CREDIT_CARD`, and `LOCATION`.
That file is the Presidio engine/recognizer configuration; `guardrails.yaml` remains the
app-level guard policy. In particular, `guardrails.input.pii.presidio_score_threshold`
can override the runtime threshold, but it does not replace the recognizer registry,
regex flags, or NLP model setup defined in `presidio_config.yaml`.
Input PII blocks the request immediately. Output PII remains a rewrite signal; if
the rewritten answer still triggers output PII, the pipeline falls back instead of
retrying indefinitely.

All non-PII guards use the central Guardrail OpenAI model configured via `selectors.guardrail: openai` and `guardrail.openai.model`. Their runtime contract is decision-based: the model returns the final guard action such as `allow`, `block`, `handoff`, `rewrite`, or `fallback`, and traces record that action plus the textual reason. There is no additional score threshold in the LLM guard decision path.

Blocked or handoff turns stay in session memory unless the input was actually sanitized by the PII guard. This preserves follow-up context for later guardrail checks while still preventing sensitive values from being persisted.

Guardrail child observations also record whether a decision came from a `pii_detector`, `heuristic`, or `llm`, and whether an LLM call was made at all.

## Quality & Test Commands

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check src --output-format concise
uv run pytest --collect-only
uv run pytest -m "not slow and not network"
uv run pytest -m "integration and not network"
uv run pytest -m "integration and network"
```

Frontend verification:

```bash
cd frontend
npm run build
```

## Type Checking (ty)

`ty` is integrated as a blocking type checker for production code (`src/`):

- Standard command: `uv run ty check src --output-format concise`

Note:
- `ty` currently checks type correctness, but does not enforce "strict missing annotation" rules.
- For explicit annotation enforcement later, use Ruff `ANN` rules in addition to `ty`.

## Workflow Guides

- `GH_CLI_BEST_PRACTICES.md`: practical `git` + GitHub CLI workflow for branch/PR/review/merge/worktree operations.

## Troubleshooting

- `integration and network` fails/skips:
  - The current network integration test is Ollama-specific.
  - Ensure Ollama is reachable at `LLM__OLLAMA__BASE_URL` and required local models are available (`ollama list`).
- API startup fails with Langfuse error:
  - Set valid Langfuse keys/host, or for local testing set `langfuse.fail_fast: false` in `src/customer_bot/config/defaults/observability.yaml`.
  - Adjust `langfuse.tracing_environment` and `langfuse.release` in `src/customer_bot/config/defaults/observability.yaml` if you want native environment/release filters in Langfuse.
- API startup fails with provider key error:
  - Ensure the provider API key is set for the active provider (`OPENAI_API_KEY` when using OpenAI-backed LLMs or embeddings).
- Frontend cannot reach the backend:
  - Ensure the API is running on `http://127.0.0.1:8000` or update the repo root `.env` with `VITE_API_BASE_URL`.
  - If thumbs up/down feedback should reach Langfuse, ensure `LANGFUSE_PUBLIC_KEY` is set in the repo root `.env`; if you use a non-default Langfuse host, also set `LANGFUSE_HOST`.
  - If you change the frontend dev port away from `5173`, update the backend CORS allowlist in `src/customer_bot/config/defaults/api.yaml`.
- Ollama `keep_alive` error (invalid duration):
  - Use a valid value like `10m`, `1h`, `0`, or leave unset/empty depending on your setup.
- Ingestion fails:
  - FAQ CSV requires `faq_id`, `question`, `answer`.
  - Product CSV requires `product_id`, `name`, `description`.

## Repository Layout

- `src/`: application code
- `dataset/`: FAQ and product corpora (defaults: `dataset/corpus.csv`, `dataset/products.csv`)
- `tests/`: unit and integration tests
- `pyproject.toml`: scripts, dependencies, tooling config
- `AGENTS.md`: repository rules for coding agents

## Optional: Langfuse via Docker Compose

A `docker-compose.yaml` is included for local Langfuse infrastructure.
Use it if you want local tracing backend services; it is optional for core API + ingest testing.
