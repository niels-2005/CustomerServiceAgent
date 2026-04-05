# customer-bot

FastAPI + LlamaIndex customer support agent for FAQ-style chat.

This project provides a local-first v1 stack:
- FastAPI API (`/health`, `/chat`)
- CSV ingestion into Chroma
- Ollama-backed LLM + embeddings
- Session-scoped short-term memory
- Optional Langfuse tracing via OpenInference

## What This Project Is

`customer-bot` is a retrieval-backed support assistant for FAQ workloads.
You ingest a CSV corpus, start the API, and send user messages to `/chat`.
The agent retrieves FAQ candidates from Chroma and returns an answer (or a safe fallback if no good match exists).

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
- Local Ollama running (`http://localhost:11434` by default)
- Required Ollama models pulled locally (from your `.env`):
  - chat model, e.g. `qwen3.5:9b`
  - embedding model, e.g. `qwen3-embedding:0.6b`

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
{"answer":"...","session_id":"..."}
```

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
| API | `API_HOST`, `API_PORT` |
| Ollama LLM | `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_REQUEST_TIMEOUT_SECONDS`, `OLLAMA_THINKING`, `OLLAMA_CONTEXT_WINDOW`, `OLLAMA_KEEP_ALIVE` |
| Ollama Embeddings | `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_EMBEDDING_NUM_CTX` |
| Chroma / Data | `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`, `CORPUS_CSV_PATH`, `TEXT_INGESTION_MODE` |
| Retrieval / Memory | `RETRIEVAL_TOP_K`, `SIMILARITY_CUTOFF`, `MEMORY_MAX_TURNS`, `FALLBACK_TEXT` |
| Langfuse | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_FAIL_FAST` |

`TEXT_INGESTION_MODE` only accepts:
- `question_only`
- `answer_only`
- `question_answer`

## Quality & Test Commands

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pytest --collect-only
uv run pytest -m "not slow and not network"
uv run pytest -m "integration and not network"
uv run pytest -m "integration and network"
```

## Troubleshooting

- `integration and network` fails/skips:
  - Ensure Ollama is reachable at `OLLAMA_BASE_URL`.
  - Ensure required local models are available (`ollama list`).
- API startup fails with Langfuse error:
  - Set valid Langfuse keys/host, or for local testing set `LANGFUSE_FAIL_FAST=false`.
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
