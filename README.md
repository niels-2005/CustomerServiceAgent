# customer-bot

FastAPI + LlamaIndex customer support agent for FAQ-style chat.

This project provides a local-first v1 stack:
- FastAPI API (`/health`, `/chat`)
- CSV ingestion into a pluggable vector backend (default: Chroma)
- Provider-based LLM + embeddings (Ollama, OpenAI)
- Session-scoped short-term memory
- Optional Langfuse tracing via OpenInference
- Request IDs, structured API errors, baseline CORS/trusted-host protection, and rate limiting

## What This Project Is

`customer-bot` is a retrieval-backed support assistant for FAQ workloads.
You ingest a CSV corpus, start the API, and send user messages to `/chat`.
The agent retrieves FAQ candidates from the configured vector backend (default: Chroma) and returns an answer (or a safe fallback if no good match exists).

## Current v1 Capabilities

- `GET /health` for service health.
- `POST /chat` with:
  - required: `user_message`
  - optional: `session_id`
- CSV ingestion CLI (`customer-bot-ingest`) with schema validation.
- Deterministic full-rebuild ingestion behavior (no uncontrolled duplication).
- Session memory isolation by `session_id`.
- Config-driven text ingestion mode:
  - `question_only`
  - `answer_only`
  - `question_answer`

## Prerequisites

- Python `>=3.11`
- `uv` installed
- Configure `.env` with `LLM_PROVIDER` and `EMBEDDING_PROVIDER`
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

3. Ingest FAQ corpus:

```bash
uv run customer-bot-ingest
```

4. Start API:

```bash
uv run customer-bot-api
```

By default, API is available at `http://127.0.0.1:8000`.

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

## Configuration (.env)

Key settings (see `.env.example` for full list):

| Group | Keys |
|---|---|
| API | `API_HOST`, `API_PORT`, `API_MAX_USER_MESSAGE_LENGTH`, `API_CORS_ALLOW_ORIGINS`, `API_CORS_ALLOW_CREDENTIALS`, `API_CORS_ALLOW_METHODS`, `API_CORS_ALLOW_HEADERS`, `API_TRUSTED_HOSTS`, `API_CHAT_RATE_LIMIT` |
| Provider selectors | `LLM_PROVIDER` (`ollama`, `openai`), `EMBEDDING_PROVIDER` (`ollama`, `openai`) |
| Provider API keys | `OPENAI_API_KEY` |
| Ollama (LLM + Embeddings) | Required: `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`; Optional connection and tuning keys are documented in `.env.example` as commented entries (`OLLAMA_BASE_URL`, `OLLAMA_REQUEST_TIMEOUT_SECONDS`, `OLLAMA_THINKING`, `OLLAMA_CONTEXT_WINDOW`, `OLLAMA_TEMPERATURE`, `OLLAMA_PROMPT_KEY`, `OLLAMA_JSON_MODE`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_EMBEDDING_BATCH_SIZE`, `OLLAMA_EMBEDDING_KEEP_ALIVE`, `OLLAMA_EMBEDDING_QUERY_INSTRUCTION`, `OLLAMA_EMBEDDING_TEXT_INSTRUCTION`, `OLLAMA_EMBEDDING_NUM_CTX`). |
| OpenAI (LLM + Embeddings) | Required: `OPENAI_LLM_MODEL`, `OPENAI_EMBEDDING_MODEL`; Optional tuning keys are documented in `.env.example` as commented entries. |
| Chroma default backend / Data | `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`, `CORPUS_CSV_PATH`, `TEXT_INGESTION_MODE` |
| Retrieval / Memory | `RETRIEVAL_TOP_K`, `SIMILARITY_CUTOFF`, `MEMORY_MAX_TURNS` |
| Agent behavior | `AGENT_DESCRIPTION`, `AGENT_SYSTEM_PROMPT`, `NO_MATCH_INSTRUCTION`, `FAQ_TOOL_DESCRIPTION`, `AGENT_TIMEOUT_SECONDS`, `ERROR_FALLBACK_TEXT` |
| Guardrails global | `GUARDRAILS_ENABLED`, `GUARDRAILS_FAIL_CLOSED`, `GUARDRAILS_MAX_OUTPUT_RETRIES`, `GUARDRAILS_TRACE_INPUTS`, `GUARDRAILS_TRACE_OUTPUTS`, `GUARDRAILS_TRACE_INCLUDE_CONFIG`, `GUARDRAILS_TRACE_INCLUDE_SCORES` |
| Guardrails provider | `GUARDRAIL_PROVIDER`, `OPENAI_GUARDRAIL_MODEL` and the optional `OPENAI_GUARDRAIL_*` overrides |
| Guardrails input | `GUARDRAILS_INPUT_PII_*`, `GUARDRAILS_PROMPT_INJECTION_*`, `GUARDRAILS_TOPIC_RELEVANCE_*`, `GUARDRAILS_ESCALATION_*` |
| Guardrails output | `GUARDRAILS_OUTPUT_PII_*`, `GUARDRAILS_GROUNDING_*`, `GUARDRAILS_BIAS_*`, `GUARDRAILS_REWRITE_*` |
| Langfuse | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_TRACING_ENVIRONMENT`, `LANGFUSE_RELEASE`, `LANGFUSE_FAIL_FAST` |

`TEXT_INGESTION_MODE` only accepts:
- `question_only`
- `answer_only`
- `question_answer`

Retrieval behavior:
- `RETRIEVAL_TOP_K` is the maximum number of matches forwarded after similarity filtering.
- if fewer matches remain after `SIMILARITY_CUTOFF`, only those remaining matches are used.

API protection defaults:
- `POST /chat` trims `user_message`, rejects blank input, and caps it via `API_MAX_USER_MESSAGE_LENGTH`.
- `session_id` is optional; blank values are normalized away before the backend decides whether to reuse or generate a session.
- CORS uses an explicit origin allowlist.
- `POST /chat` is rate-limited by `API_CHAT_RATE_LIMIT`.
- `/health` remains a simple liveness endpoint and returns `{"status":"ok"}` after successful startup.

Langfuse trace shape:
- root `input` includes `system_prompt_version`, `user_message`, and `session_id`
- root `output` includes `answer`, `thinking`, and a compact `tool_calls` overview
- full tool inputs/outputs are additionally captured as nested Langfuse `tool` observations

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

For input/output PII validation, install the Hub validator explicitly:

```bash
uv sync
uv run guardrails configure
uv run guardrails hub install hub://guardrails/detect_pii
```

The app does not auto-install Hub validators at request time. If `GUARDRAILS_ENABLED=true` and `DetectPII` is missing, startup or first guard construction fails clearly.

All non-PII guards use the central Guardrail OpenAI model configured via `GUARDRAIL_PROVIDER=openai` and `OPENAI_GUARDRAIL_MODEL`.

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
  - Ensure Ollama is reachable at `OLLAMA_BASE_URL` and required local models are available (`ollama list`).
- API startup fails with Langfuse error:
  - Set valid Langfuse keys/host, or for local testing set `LANGFUSE_FAIL_FAST=false`.
  - Set `LANGFUSE_TRACING_ENVIRONMENT` and `LANGFUSE_RELEASE` if you want native environment/release filters in Langfuse.
- API startup fails with provider key error:
  - Ensure the provider API key is set for the active provider (`OPENAI_API_KEY` when using OpenAI-backed LLMs or embeddings).
- Ollama `keep_alive` error (invalid duration):
  - Use a valid value like `10m`, `1h`, `0`, or leave unset/empty depending on your setup.
- Ingestion fails:
  - Confirm CSV includes required columns: `faq_id`, `question`, `answer`.

## Repository Layout

- `src/`: application code
- `dataset/`: FAQ corpus (default `dataset/corpus.csv`)
- `tests/`: unit and integration tests
- `pyproject.toml`: scripts, dependencies, tooling config
- `AGENTS.md`: repository rules for coding agents

## Optional: Langfuse via Docker Compose

A `docker-compose.yaml` is included for local Langfuse infrastructure.
Use it if you want local tracing backend services; it is optional for core API + ingest testing.
