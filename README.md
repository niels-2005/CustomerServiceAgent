# CustomerServiceAgent

<div align="center">

**An agentic AI customer support system with RAG, safety guardrails, and traceable decision flows**

![Python](https://img.shields.io/badge/Python-14354C?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-111827?style=for-the-badge&logo=llama&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6584?style=for-the-badge&logo=databricks&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Langfuse](https://img.shields.io/badge/Langfuse-F97316?style=for-the-badge&logo=datadog&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)

</div>

`CustomerServiceAgent` is a project that demonstrates a modern AI support assistant for a simulated e-commerce company called `NexaMarket`. It combines FastAPI, LlamaIndex, dual-source retrieval, explicit guardrails, Langfuse tracing, and a simple React frontend into one end-to-end system.

The goal is to show how an LLM application can be structured like a real backend product: grounded retrieval, explicit contracts, safety layers, session handling, observability, and a clearly defined HTTP interface. In practical terms, the system is designed to improve customer satisfaction while reducing support workload by handling common support questions quickly and consistently.

## Project Overview

**NexaSupport for NexaMarket** is the demo assistant inside this repository. Users can ask about products, account topics, shipping, returns, payments, and other support-related workflows through a chat interface backed by a FastAPI backend.

What makes the project interesting is the combination of agentic retrieval and safety engineering. Instead of relying on a single prompt and static context injection, the system uses a LlamaIndex function agent with explicit tools, separate FAQ and product retrieval flows, input and output guardrails, and Langfuse traces that make the full decision path inspectable.

The API also includes practical HTTP protections such as configurable Redis-backed rate limiting, trusted-host enforcement, CORS allowlisting, request IDs, and defensive response headers. There is currently no authentication or authorization layer because the API is designed to be reachable directly from the website without requiring a user login.

## Demo 🎬

![Bot Demo](images/bot_demo.gif)

## Problem & Motivation 🎯

Large language models are powerful, but they do not reliably know company-specific product catalogs, support policies, or internal FAQ content. In a real support context, that becomes a grounding problem: the model may sound confident while lacking the data it actually needs.

This project addresses that problem with a retrieval-augmented architecture. FAQ data and product data are ingested separately, embedded into a vector store, and exposed to the agent through two explicit tools: `faq_lookup` and `product_lookup`. These were deliberately separated because they solve different retrieval tasks. A product search should not be forced through the FAQ path, and a support-policy lookup should not be treated like product discovery. Keeping them separate makes ingestion, retrieval, and ongoing maintenance more explicit.

Compared with standard RAG, which typically retrieves vector context once and appends it to an LLM prompt, the agentic setup is more flexible. The agent can decide which tool to call, with which parameters, and those parameters can differ from the raw user input. If an initial tool result is incomplete or not specific enough, the agent can autonomously reformulate the lookup and call a tool again before producing the final answer. It can also decide to stop and return that no reliable information was found instead of forcing an unsupported answer.

The two-tool setup also keeps FAQ and product ingestion/retrieval flows independent. That makes it easier to update either side of the knowledge base without changing the overall agent flow. Compared with fine-tuning, this is operationally simpler when FAQs, policies, or product data change frequently, because the corpora can be updated and re-ingested without re-training the model each time.

That flexibility comes with tradeoffs. The agentic approach introduces more latency than a simpler single-pass RAG flow, and more autonomy does not automatically mean better results. In practice, a more autonomous system usually requires more prompt tuning, tool design, guardrail design, and evaluation to stay reliable.

The broader motivation is reusability, extensibility, and configuration-driven flexibility. The current demo uses simulated AI-generated NexaMarket data, but the architecture is designed so the underlying corpora can be replaced for another company or domain without changing the overall flow. Non-secret runtime behavior is centralized in `src/customer_bot/config/defaults/`, which makes experimentation easier, and provider/runtime wiring is explicit and centralized so additional compatible backends could be added later without changing the overall architecture. Around that, guardrails and tracing make the system more realistic for production-style support scenarios.

## Key Features ✨

### Agentic support workflow

- LlamaIndex `FunctionAgent` with two explicit tools: `faq_lookup` and `product_lookup`
- Tool usage and final agent outputs are observable in traces, including inputs, outputs, and no-match behavior
- Safe fallback responses when the agent or safety pipeline cannot return a reliable answer

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

- Langfuse is the optional tracing backend for the chat pipeline and frontend feedback flow
- Traces include agent steps, guardrails, tools, metadata, and user feedback

### Practical backend engineering

- Typed FastAPI request and response contracts
- Redis-backed LLM chat-history memory scoped by `session_id`, shared across API instances, with a rolling 24-hour TTL to keep the API stateless across restarts and scaling
- Configurable Redis-backed rate limiting with a global default limit, a stricter `/chat` budget, trusted-host enforcement, CORS allowlisting, request IDs, and defensive response headers

## System Architecture 🏗️

```mermaid
flowchart LR
    A[User] --> B[React Frontend]
    B --> C[FastAPI /chat]
    C <--> M[Redis<br/>session memory + rate limits]

    C --> D[Input PII / Secret Guard]
    D -->|Clean input| E[Parallel Input Guards]
    D -->|PII detected| R1[Blocked response]

    E -->|Allow| F[LlamaIndex Agent]
    E --> E1[Prompt Injection]
    E --> E2[Escalation]
    E --> E3[Topic Relevance]

    E1 -->|Block| R2[Blocked response]
    E2 -->|Handoff| R3[Handoff response]
    E3 -->|Off-topic| R4[Off-topic response]

    F --> T1[faq_lookup]
    F --> T2[product_lookup]
    F --> G[Output PII / Secret Guard]

    G -->|Clean output| I[Parallel Output Guards]
    G -->|PII detected| H[Rewrite]

    I --> I1[Grounding]
    I --> I2[Bias]

    I1 -->|Allow| K[Final assistant response]
    I2 -->|Allow| K
    I1 -->|Rewrite| H
    I2 -->|Rewrite| H
    I1 -->|Fallback| R5[Fallback response]
    I2 -->|Fallback| R5

    H --> J[Re-run Output Guards]
    J -->|Allow| K
    J -->|Fail again| R5

    K --> Q[API response]
    R1 --> Q
    R2 --> Q
    R3 --> Q
    R4 --> Q
    R5 --> Q
    Q --> C
    C --> B
    B --> A

    L[Langfuse]
    D -. traced .- L
    E -. traced .- L
    F -. traced .- L
    G -. traced .- L
    I -. traced .- L
    H -. traced .- L
    J -. traced .- L
    B -. feedback .- L
```

The current request flow is intentionally explicit. Input PII runs first and can block the request immediately before any later guard or trace sees the original detected sensitive content. If that stage passes, the input LLM guards run in parallel. When multiple input issues are detected, the decision priority is `prompt_injection` before `escalation` before `topic_relevance`. If the input guard stage passes, the LlamaIndex agent is executed with the available retrieval tools.

On the output side, output PII runs before semantic output checks because it can trigger a rewrite without waiting for the grounding or bias checks. After that, `grounding` and `bias` evaluate the answer in parallel. Each output guard can allow the answer, request a rewrite, or force a fallback depending on the situation. If a rewrite is requested, the rewritten answer is passed through the output-guard stage again. Rewrite is useful when an answer is still recoverable, while fallback is used when a response is no longer safe or reliable enough to repair. If a guard falls back, the configured fallback response is returned. How often rewrites can happen depends on `guardrails.global.max_output_retries` in `src/customer_bot/config/defaults/guardrails.yaml`.

This separation is deliberate. Safety-critical checks such as prompt injection, escalation, grounding, and output bias were modeled as explicit guardrails instead of additional agent tools so the main agent is not overloaded with too many competing responsibilities. In practice, this makes the system easier to reason about, easier to tune, and easier to observe.

Outside the guardrail and agent decision flow, Redis supports the shared operational state that keeps session memory and API rate limiting consistent across instances.

### Why Redis for Session Memory

The first version used in-memory session state directly inside the API process. That approach was simple, but it meant chat history was lost on every restart and horizontal scaling would have required sticky routing so each user always reached the same machine. Redis removes that coupling by making short-term session memory shared across API instances, which keeps the API stateless in this area.

I also considered passing the chat history back and forth as part of each API request. That would have worked because session history is already bounded, but it would have inflated every `/chat` payload and pushed transient conversation state into the public API contract. Redis keeps that state server-side instead. The tradeoff is an explicit infrastructure dependency, but the request shape stays smaller and the client does not need to resubmit prior turns on every message.

Redis was chosen over Postgres because this project is a customer-support agent, not a system of record for long-lived conversations. The session history only needs to exist briefly so the agent can answer follow-up questions consistently, and then it should disappear automatically. Persisting the same conversations in the application database would currently add little value, because Langfuse already captures traces and chat-level observability for inspection and analysis. That matches Redis well: it is fast, already part of the local infrastructure, and the current memory backend can enforce a rolling TTL of `86400` seconds (24 hours) via `src/customer_bot/config/defaults/memory.yaml`.

The history is also intentionally capped through `memory.max_turns` in `src/customer_bot/config/defaults/memory.yaml`, currently at `20` stored messages, which corresponds to `10` user turns with one assistant reply each. That limit fits the customer-support use case, where chats are usually short and task-focused. It also avoids introducing more complex context-management strategies too early, so the initial design choice here is a fixed bounded history instead.

## Installation ⚙️

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

1. Clone the repository.

```bash
git clone git@github.com:niels-2005/CustomerServiceAgent.git
cd CustomerServiceAgent
```

2. Install backend dependencies.

```bash
uv sync
```

3. Create the local environment file.

```bash
cp .env.example .env
```

4. Configure your model provider.

- For OpenAI, set `OPENAI_API_KEY` in `.env`.
- For Ollama, ensure Ollama is running locally and review the provider selection in `src/customer_bot/config/defaults/providers.yaml`.

5. Start the required local infrastructure.

```bash
docker compose up -d redis
```

`redis` is a named service in `docker-compose.yaml`, so this starts the minimum required infrastructure for `/chat`. Make sure `CHAT_MEMORY_REDIS_URL` and `RATE_LIMIT_REDIS_URL` in `.env` point to that reachable Redis instance.

6. Install the Presidio language model used by the PII guardrails.

```bash
uv run python -m spacy download de_core_news_md
```

7. Ingest the FAQ and product sources.

```bash
uv run customer-bot-ingest --source faq
uv run customer-bot-ingest --source products
```

8. Start the API.

```bash
uv run customer-bot-api
```

The backend is available at `http://127.0.0.1:8000`.

9. Start the frontend.

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.

### Optional: Full Local Observability Stack

If you also want the full local Langfuse stack with dashboards and traces, start the complete Compose setup:

```bash
docker compose up -d
```

Then:

1. Open `http://localhost:3000`
2. Create an organization and project
3. Generate API keys
4. Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env`

Once configured, the backend returns `trace_id` values on chat responses and the frontend can attach thumbs up/down feedback to the same Langfuse trace.

If you do not want Langfuse to block local startup, set `langfuse.fail_fast: false` in `src/customer_bot/config/defaults/observability.yaml`. Otherwise the API can fail during startup when Langfuse keys are missing or the host is unreachable.

Redis is still required even when Langfuse is disabled because the application uses it for short-term chat-history memory and shared API rate limiting.

## API Snapshot 🔌

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

- `status` signals the final outcome of the turn and can currently be `answered`, `blocked`, `handoff`, `fallback`, or `session_limit`
- `guardrail_reason` explains why a guardrail changed the outcome when applicable and can currently be `null`, `secret_pii`, `prompt_injection`, `off_topic`, `escalation`, `output_sensitive_data`, `grounding`, `bias`, or `guardrail_error`
- `handoff_required` allows the frontend to trigger a human-support flow later
- `retry_used` indicates that an output rewrite was attempted
- `sanitized` indicates that sensitive content was removed or masked during processing
- `trace_id` links the turn to its Langfuse trace when observability is configured
- `session_limit` tells the client that the short-term chat history reached the configured cap of 20 stored messages, which corresponds to 10 user turns with one assistant reply each

Swagger UI is available at `http://127.0.0.1:8000/docs`.

## Project Structure 🗂️

```text
.
├── src/customer_bot/
│   ├── agent/              # LlamaIndex agent orchestration and tool wiring
│   ├── api/                # FastAPI routes, middleware, errors, and app bootstrap
│   ├── chat/               # top-level chat orchestration across memory, agent, and guardrails
│   ├── config/             # settings models and versioned YAML defaults
│   ├── guardrails/         # input/output guardrails, rewrite flow, and tracing helpers
│   ├── ingest/             # ingestion CLI entrypoints
│   ├── llm_providers/      # OpenAI and Ollama provider integrations
│   ├── memory/             # Redis-backed short-term session memory
│   ├── retrieval/          # corpus ingestion, vector storage, and retrieval services
│   ├── model_factory.py    # provider/model construction and wiring
│   └── observability.py    # Langfuse observability bootstrap
├── frontend/               # simple React/Vite demo frontend
├── dataset/                # FAQ and product source data
├── tests/                  # unit and integration tests
├── images/                 # demo and gallery assets
├── docker-compose.yaml     # local infrastructure stack with Redis and the full Langfuse services
└── pyproject.toml          # dependencies, scripts, tooling
```

## Roadmap 🚀

- Evaluate migrating local Chroma persistence to Postgres with `pgvector` or a similar production-oriented backend
- Build deterministic evaluation datasets for API and guardrail behavior
- Add a separate evaluation dataset for non-deterministic cases and evaluate it via human annotation or LLM-as-a-judge, with LLM-as-a-judge currently being the preferred direction to gain experience with that workflow
- Reduce application latency. In the current demo, a request can take around 6 seconds, so planned experiments include running the agent in parallel with the input guardrail stage, exploring streaming after input PII passes, and testing whether a small fine-tuned language model on the FAQ and product data could reduce tool dependence and response time
- Reduce API cost and latency with targeted caching so repeated retrieval, guardrail, or other reusable computations do not trigger the same work and model costs again when a safe cached result would be sufficient
- Add CI/CD with linting, typing, unit tests, integration tests, container builds, vulnerability scanning, and deployment automation
- Continue tightening guardrail quality, especially around rewrite behavior and measurable false-positive rates
- And probably much more!

## Gallery 🖼️

<details>
<summary>🖼️ Show Gallery</summary>

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

</details>

## Verification ✅

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
