# CustomerServiceAgent

<div align="center">

**An agentic AI customer support system with RAG, safety guardrails, and traceable decision flows**

![Python](https://img.shields.io/badge/Python-14354C?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-111827?style=for-the-badge&logo=llama&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6584?style=for-the-badge&logo=databricks&logoColor=white)
![Langfuse](https://img.shields.io/badge/Langfuse-F97316?style=for-the-badge&logo=datadog&logoColor=white)
![OpenInference](https://img.shields.io/badge/OpenInference-0F172A?style=for-the-badge&logo=openai&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)

</div>

`CustomerServiceAgent` is a portfolio project that demonstrates a modern AI support assistant for a simulated e-commerce company called `NexaMarket`. It combines FastAPI, LlamaIndex, dual-source retrieval, explicit guardrails, Langfuse tracing, and a simple React frontend into one end-to-end system.

The goal is to show how an LLM application can be structured like a real backend product: grounded retrieval, explicit contracts, safety layers, session handling, observability, and a clearly defined HTTP interface.

## Project Overview

**NexaSupport for NexaMarket** is the demo assistant inside this repository. Users can ask about products, account topics, shipping, returns, payments, and other support-related workflows through a chat interface backed by a FastAPI backend.

What makes the project interesting is the combination of agentic retrieval and safety engineering. Instead of relying on a single prompt and static context injection, the system uses a LlamaIndex function agent with explicit tools, separate FAQ and product retrieval flows, input and output guardrails, and Langfuse traces that make the full decision path inspectable.

The API also includes practical HTTP protections such as rate limiting, trusted-host enforcement, CORS allowlisting, request IDs, and defensive response headers. There is currently no authentication or authorization layer because the API is designed to be reachable directly from the website without requiring a user login.

## Demo

![Bot Demo](images/bot_demo.gif)

## Problem & Motivation

Large language models are powerful, but they do not reliably know company-specific product catalogs, support policies, or internal FAQ content. In a real support context, that becomes a grounding problem: the model may sound confident while lacking the data it actually needs.

This project addresses that problem with a retrieval-augmented architecture. FAQ data and product data are ingested separately, embedded into a vector store, and exposed to the agent through two explicit tools: `faq_lookup` and `product_lookup`.

The agentic approach matters because it goes beyond a simple "retrieve once, answer once" RAG pattern. The agent can decide which tool to call, with which parameters, and those parameters can differ from the raw user input. It can also perform iterative tool calls before producing the final answer and react explicitly when no reliable match exists. Around that, guardrails and tracing make the system more realistic for production-style support scenarios.

The broader motivation is reusability. The current demo uses simulated AI-generated NexaMarket data, but the architecture is designed so the underlying corpora can be replaced for another company or domain without changing the overall flow.

## Key Features

### Agentic support workflow

- LlamaIndex `FunctionAgent` with two explicit tools: `faq_lookup` and `product_lookup`
- Tool usage and final agent outputs are observable in traces, including inputs, outputs, and no-match behavior
- Safe fallback behavior when the agent cannot produce a reliable grounded answer

### Dual-source retrieval

- Separate ingestion pipelines for FAQ and product corpora
- CSV schema validation for deterministic ingestion contracts
- Local Chroma persistence with independently configurable collections and retrieval thresholds

### Guardrail pipeline

- Deterministic input PII and secret detection before the parallel input guardrails
- Parallel input guardrails for prompt injection, escalation, and topic relevance
- Agent execution only after the input guard stage passes
- Deterministic output PII detection before semantic output checks
- Parallel output guardrails for grounding and bias, followed by allow, rewrite, or fallback depending on the result

### Observability and feedback

- OpenInference instrumentation is installed explicitly by the observability bootstrap for the LlamaIndex execution layer
- Langfuse is the optional tracing backend/client used on top of that instrumentation when observability is configured successfully
- Traces include agent steps, guardrails, tools, metadata, and frontend user feedback

### Practical backend engineering

- Typed FastAPI request and response contracts
- Session-based conversation memory scoped by `session_id`
- Rate limiting, trusted-host enforcement, CORS allowlisting, request IDs, and defensive response headers

## System Architecture

```mermaid
flowchart TD
    A[User] --> B[React Frontend]
    B --> C[FastAPI POST /chat]

    C --> D[Input PII / Secret Guard]
    D -. traced .- L[OpenInference + Langfuse]
    D -->|PII detected| R1[Blocked response]
    D -->|Clean input| E[Parallel Input Guards]

    E --> E1[Prompt Injection]
    E --> E2[Escalation]
    E --> E3[Topic Relevance]
    E -. traced .- L

    E1 -->|Block| R2[Blocked response]
    E2 -->|Handoff| R3[Handoff response]
    E3 -->|Off-topic| R4[Blocked response]
    E -->|Allow| F[LlamaIndex Agent]

    F --> T1[faq_lookup]
    F --> T2[product_lookup]
    F -. traced .- L

    F --> G[Output PII / Secret Guard]
    G -->|Sensitive data| H[Rewrite]
    G -->|Clean output| I[Parallel Output Guards]

    I --> I1[Grounding]
    I --> I2[Bias]
    I -. traced .- L

    I1 -->|Allow| K[Final assistant response]
    I2 -->|Allow| K
    I1 -->|Rewrite| H
    I2 -->|Rewrite| H
    I1 -->|Fallback| R5[Fallback response]
    I2 -->|Fallback| R5

    H --> J[Re-run Output Guards]
    J -->|Allow| K
    J -->|Fail again| R5

    K --> B
    R1 --> B
    R2 --> B
    R3 --> B
    R4 --> B
    R5 --> B
    B --> A
    B -. feedback .- L
```

The current request flow is intentionally explicit. Input PII runs first and can block the request immediately before any later guard or trace sees the original sensitive content. If that stage passes, the input LLM guards run in parallel. When multiple input issues are detected, the decision priority is `prompt_injection` before `escalation` before `topic_relevance`. If the input guard stage passes, the LlamaIndex agent is executed with the available retrieval tools.

On the output side, output PII runs before semantic output checks because it can trigger a rewrite without waiting for the grounding or bias checks. After that, `grounding` and `bias` run in parallel. If a rewrite is requested, the rewritten answer is checked again. How often that can happen depends on `guardrails.global.max_output_retries` in `src/customer_bot/config/defaults/guardrails.yaml`. If the answer still fails after the configured retry budget, the pipeline returns a safe fallback.

## Installation

### Prerequisites

- Python `>=3.11`
- `uv`
- Docker Desktop or Docker Engine with Compose support
- Recommended: review the versioned defaults in `src/customer_bot/config/defaults/` before running the stack so you understand provider selection, guardrail behavior, API limits, and observability settings
- One model provider:
  - OpenAI with `OPENAI_API_KEY`
  - or local Ollama with pulled models
- Important: with the current defaults, OpenAI-backed configuration is the easiest path and Langfuse startup is fail-fast by default, so missing Langfuse keys or an unreachable Langfuse host can block startup unless you disable fail-fast in `src/customer_bot/config/defaults/observability.yaml`

### Quick Start

1. Install backend dependencies.

```bash
uv sync
```

2. Create the local environment file.

```bash
cp .env.example .env
```

3. Configure your model provider.

- For OpenAI, set `OPENAI_API_KEY` in `.env`.
- For Ollama, ensure Ollama is running locally and review the provider selection in `src/customer_bot/config/defaults/providers.yaml`.

4. Install the Presidio language model used by the PII guardrails.

```bash
uv run python -m spacy download de_core_news_md
```

5. Ingest the FAQ and product sources.

```bash
uv run customer-bot-ingest --source faq
uv run customer-bot-ingest --source products
```

6. Start the API.

```bash
uv run customer-bot-api
```

The backend is available at `http://127.0.0.1:8000`.

7. Start the frontend.

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.

### Optional: Local Langfuse Setup

If you want end-to-end traces and dashboards, start the local Langfuse stack:

```bash
docker compose up -d
```

Then:

1. Open `http://localhost:3000`
2. Create an organization and project
3. Generate API keys
4. Add `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` to `.env`

Once configured, the backend returns `trace_id` values on chat responses and the frontend can attach thumbs up/down feedback to the same Langfuse trace.

If you do not want to run Langfuse locally, set `langfuse.fail_fast: false` in `src/customer_bot/config/defaults/observability.yaml`. Otherwise the API can fail during startup when Langfuse keys are missing or the host is unreachable.

## API Snapshot

The public API is intentionally small:

- `GET /health` returns `{"status":"ok"}`
- `POST /chat` accepts:
  - `user_message` as required input
  - `session_id` as optional session continuity input

A `/chat` response can look like this:

```json
{
  "answer": "Ich habe hierzu keine verlaesslichen Informationen gefunden. Kannst du mir die genaue Produktbezeichnung nennen?",
  "session_id": "7e3d5f14-7f43-4a77-a7fb-f7f56ad7ef1c",
  "trace_id": "3b0d9b6e5d9242b2",
  "status": "answered",
  "guardrail_reason": null,
  "handoff_required": false,
  "retry_used": false,
  "sanitized": false
}
```

Here:

- `status` signals whether the turn was answered, blocked, handed off, or downgraded to fallback
- `status` can currently be `answered`, `blocked`, `handoff`, or `fallback`
- `guardrail_reason` explains why a guardrail changed the outcome when applicable and can currently be `null`, `secret_pii`, `prompt_injection`, `off_topic`, `escalation`, `output_sensitive_data`, `grounding`, `bias`, or `guardrail_error`
- `handoff_required` allows the frontend to trigger a human-support flow later
- `retry_used` indicates that an output rewrite was attempted
- `sanitized` indicates that sensitive content was removed or masked during processing
- `trace_id` links the turn to its Langfuse trace when observability is configured

Swagger UI is available at `http://127.0.0.1:8000/docs`.

## Project Structure

- `src/customer_bot/`: backend application code
- `src/customer_bot/config/defaults/`: YAML defaults for API, providers, retrieval, guardrails, observability, and prompts
- `frontend/`: React/Vite chat frontend
- `dataset/`: FAQ and product source data
- `tests/`: unit and integration tests
- `images/`: demo and gallery assets for the project
- `docker-compose.yaml`: optional local Langfuse stack

## Roadmap

- Replace the current in-memory session history with a stateless or persistent memory strategy
- Evaluate migrating local Chroma persistence to Postgres with `pgvector` or a similar production-oriented backend
- Build deterministic evaluation datasets for API and guardrail behavior
- Add a separate evaluation dataset for non-deterministic cases and evaluate it via human annotation or LLM-as-a-judge, with LLM-as-a-judge currently being the preferred direction to gain experience with that workflow
- Reduce application latency. In the current demo, a request can take around 6 seconds, so planned experiments include running the agent in parallel with the input guardrail stage, exploring streaming after input PII passes, and testing whether a small fine-tuned language model on the FAQ and product data could reduce tool dependence and response time
- Add CI/CD with linting, typing, unit tests, integration tests, container builds, vulnerability scanning, and deployment automation
- Continue tightening guardrail quality, especially around rewrite behavior and measurable false-positive rates
- And probably much more!

## Gallery

### 1. PII Input Guardrail Triggered

![PII Input Guardrail](images/pii_input_guardrail.png)

This shows that the request is blocked before it ever reaches the agent. For this version, I intentionally chose a hard block instead of automatic redaction-and-continue behavior.

### 2. Topic Relevance Guardrail

![Topic Relevance Guardrail](images/topic_relevance_input_guardrail.png)

This demonstrates that out-of-scope questions are rejected cleanly. It also shows that the other input guardrails can still run without necessarily triggering a block.

### 3. Prompt Injection Guardrail via Heuristic

![Prompt Injection Heuristic](images/prompt_injection_guardrail_heuristic.png)

This example shows a heuristic short-circuit. The request is blocked for prompt injection without needing to call the guardrail LLM. The heuristic terms are defined in `src/customer_bot/config/defaults/guardrails.yaml` starting at line 39. You can also see that escalation and topic relevance were evaluated too, but prompt injection won because it has the higher configured priority.

### 4. Prompt Injection Guardrail via LLM

![Prompt Injection LLM](images/prompt_injection_guardrail_llm.png)

This is the LLM-based prompt injection path. It complements the heuristic layer for cases that are less obvious.

### 5. Escalation Guardrail via Heuristic

![Escalation Heuristic](images/escalation_guardrail_heuristic.png)

This example shows a heuristic short-circuit. The request is handed off for escalation without needing to call the guardrail LLM. The heuristic terms are defined in `src/customer_bot/config/defaults/guardrails.yaml` starting at line 137.

### 6. Escalation Guardrail via LLM

![Escalation LLM](images/escalation_guardrail_llm.png)

This shows a more contextual escalation decision. The current system does not directly connect to a human, but it returns `status="handoff"` and `handoff_required=true` so a frontend could initiate the next step.

### 7. Complete Flow Through the Pipeline

![Complete Flow](images/complete_flow.png)

This is the clearest end-to-end trace view: input guardrails, agent execution, tool usage, and output guardrails in one request lifecycle.

### 8. Product No-Match Behavior

![Product No Match](images/product_not_found.png)

This demonstrates that the bot remains reliable when no product match exists instead of hallucinating unsupported details.

### 9. Output PII Guardrail

![Output PII Guardrail](images/pii_output_guardrail.png)

The output is scanned for sensitive data. If needed, a rewrite is triggered and the revised answer is checked again.

### 10. Grounding Guardrail

![Grounding Guardrail](images/grounding_guardrail.png)

This checks whether the final answer is actually supported by retrieval evidence and execution context, with `allow`, `rewrite`, or `fallback` as possible outcomes. In practice, `rewrite` is useful when the answer is mostly grounded but needs tightening, while `fallback` is used when the answer contains unsupported or contradictory claims.

### 11. Bias Guardrail

![Bias Guardrail](images/bias_guardrail.png)

This checks the assistant answer for potentially harmful or biased phrasing, with `allow`, `rewrite`, or `fallback` as possible outcomes. `Rewrite` is appropriate when the answer is recoverable, while `fallback` is the safer option if the response cannot be repaired reliably.

### 12. Langfuse Default Dashboard

![Langfuse Default Dashboard 1](images/langfuse_default_dashboard_1.png)
![Langfuse Default Dashboard 2](images/langfuse_default_dashboard_2.png)

Langfuse already provides a strong default dashboard for costs, latencies, and trace-level visibility out of the box.

### 13. Custom Metrics Dashboard

![Custom Metrics Dashboard](images/custom_metrics_dashboard.png)

This custom dashboard tracks higher-level system signals such as guardrail triggers, successful answers, rewrites, and no-match behavior. Langfuse does not currently calculate rates directly in this setup, so derived metrics need to be computed manually. For example, an escalation rate here would be `2 / 17 = 0.11`.

### 14. Trace Filtering for Escalations

![Escalation Trace Filtering](images/escalation_guardrail_filtered.png)

Because the API emits structured metadata such as `status`, traces can be filtered for specific operational cases. Escalation is just one example; the same approach can be used for other workflows and error states.

### 15. Session History in Langfuse

![Session History](images/session_history.png)

Langfuse also makes it easy to inspect conversation history per session and analyze how multi-turn interactions evolve.

### 16. Filtering Negative Feedback

![Thumbs Down Filtering](images/thumbs_down_filtering.png)

This view shows how user feedback can be used to find problematic interactions quickly and inspect them in context.

## Verification

Relevant local verification commands for this project:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check src --output-format concise
uv run pytest --collect-only
uv run pytest -m unit
uv run pytest -m "not slow and not network"
uv run pytest -m "integration and not network"
uv run pytest -m "integration and network"
```
