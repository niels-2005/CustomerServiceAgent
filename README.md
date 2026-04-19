# customer-bot

FastAPI + LlamaIndex customer support agent for FAQ-style chat.

This project provides a local-first v1 stack:
- FastAPI API (`/health`, `/chat`)
- CSV ingestion into a pluggable vector backend (default: Chroma)
- Provider-based LLM + embeddings (Ollama, OpenAI, Gemini, OpenRouter LLM)
- Session-scoped short-term memory
- Optional Langfuse tracing via OpenInference

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
  - Gemini (Google GenAI): `GOOGLE_API_KEY`
  - OpenRouter LLM: `OPENROUTER_API_KEY`

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
| Provider selectors | `LLM_PROVIDER` (`ollama`, `openai`, `gemini`, `openrouter`), `EMBEDDING_PROVIDER` (`ollama`, `openai`, `gemini`) |
| Provider API keys | `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY` |
| Ollama (LLM + Embeddings) | Required: `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`; Optional connection and tuning keys are documented in `.env.example` as commented entries (`OLLAMA_BASE_URL`, `OLLAMA_REQUEST_TIMEOUT_SECONDS`, `OLLAMA_THINKING`, `OLLAMA_CONTEXT_WINDOW`, `OLLAMA_TEMPERATURE`, `OLLAMA_PROMPT_KEY`, `OLLAMA_JSON_MODE`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_EMBEDDING_BATCH_SIZE`, `OLLAMA_EMBEDDING_KEEP_ALIVE`, `OLLAMA_EMBEDDING_QUERY_INSTRUCTION`, `OLLAMA_EMBEDDING_TEXT_INSTRUCTION`, `OLLAMA_EMBEDDING_NUM_CTX`). |
| OpenAI (LLM + Embeddings) | Required: `OPENAI_LLM_MODEL`, `OPENAI_EMBEDDING_MODEL`; Optional tuning keys are documented in `.env.example` as commented entries. |
| Gemini (LLM + Embeddings) | Required: `GEMINI_LLM_MODEL`, `GEMINI_EMBEDDING_MODEL`; Optional tuning keys are documented in `.env.example` as commented entries. |
| OpenRouter (LLM only) | Required: `OPENROUTER_LLM_MODEL`; Optional tuning keys are documented in `.env.example` as commented entries (`OPENROUTER_TEMPERATURE`, `OPENROUTER_MAX_TOKENS`, `OPENROUTER_CONTEXT_WINDOW`, `OPENROUTER_MAX_RETRIES`, `OPENROUTER_API_BASE`, `OPENROUTER_ALLOW_FALLBACKS`). |
| Chroma default backend / Data | `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`, `CORPUS_CSV_PATH`, `TEXT_INGESTION_MODE` |
| Retrieval / Memory | `RETRIEVAL_TOP_K`, `SIMILARITY_CUTOFF`, `MEMORY_MAX_TURNS` |
| Agent behavior | `AGENT_DESCRIPTION`, `AGENT_SYSTEM_PROMPT`, `NO_MATCH_INSTRUCTION`, `FAQ_TOOL_DESCRIPTION`, `AGENT_TIMEOUT_SECONDS`, `ERROR_FALLBACK_TEXT` |
| Langfuse | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_TRACING_ENVIRONMENT`, `LANGFUSE_RELEASE`, `LANGFUSE_FAIL_FAST` |

`TEXT_INGESTION_MODE` only accepts:
- `question_only`
- `answer_only`
- `question_answer`

Retrieval behavior:
- `RETRIEVAL_TOP_K` is the maximum number of matches forwarded after similarity filtering.
- if fewer matches remain after `SIMILARITY_CUTOFF`, only those remaining matches are used.

Langfuse trace shape:
- root `input` includes `system_prompt_version`, `user_message`, and `session_id`
- root `output` includes `answer`, `thinking`, and a compact `tool_calls` overview
- full tool inputs/outputs are additionally captured as nested Langfuse `tool` observations

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
  - Ensure the provider API key is set for the active provider (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`).
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
