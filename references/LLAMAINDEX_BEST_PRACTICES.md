# LLAMAINDEX Best Practices (Universal, Future-Proof)

This document defines durable LlamaIndex engineering standards that are valid across projects and over time.
It focuses on the domains covered in `LLAMAINDEX_REFERENCES.md` and avoids phase-specific or version-specific implementation mandates.

## 1. Core Principles

- Prefer simple, observable architectures before introducing orchestration complexity.
- Keep data contracts explicit and validated at boundaries.
- Separate indexing from serving; treat ingestion as an independent operational workflow.
- Make retrieval behavior explicit (`top_k`, filtering, fallback policy) and testable.
- Keep model, storage, and runtime choices configurable.
- Treat agent/tool behavior as API design: clear schemas, deterministic side effects, auditable outcomes.

## 2. Agent System Design

### 2.1 Agent Pattern Selection

Choose the least complex pattern that satisfies requirements:

- Single-agent tool-calling for focused tasks.
- Multi-agent orchestration only when there are clearly distinct specialist roles.
- Custom planning loops only when built-in patterns cannot enforce needed control flow.

### 2.2 Tool Quality Rules

Tool-calling reliability depends on tool interface quality.

Rules:

- Use specific, stable names.
- Write high-signal docstrings describing when to call and expected output.
- Use strict, typed inputs.
- Keep outputs deterministic and easy to validate.
- Use `return_direct` when tool output should terminate the reasoning loop.

### 2.3 Streaming and Runtime Events

Treat streaming and event inspection as standard observability/UX capabilities.

- Use streamed agent events for long-running tasks.
- Capture tool call arguments/results for debugging and regression analysis.

## 3. RAG Pipeline Standards

### 3.1 Loading

- Use readers that match source type and operational constraints.
- Prefer explicit loaders for strict domain schemas.
- Validate source shape before node creation.

### 3.2 Transformations and Node Parsing

- Use ingestion transformations intentionally; each transformation must have a measurable value.
- Keep chunking strategy aligned to document semantics and query goals.
- Avoid default splitter usage when source records are already atomic.

### 3.3 Indexing

- Use `VectorStoreIndex` when semantic retrieval is required.
- Ensure embedding model consistency between ingest and query paths.
- Keep index creation idempotent where operationally possible.

### 3.4 Querying

Treat querying as three explicit stages:

- Retrieval
- Postprocessing
- Response synthesis

Rules:

- Make retrieval parameters explicit.
- Define no-match behavior explicitly.
- Keep synthesis mode aligned to latency/quality constraints.

### 3.5 Storing

- Persist indexes and/or vector stores to avoid repeated re-indexing.
- Keep storage configuration environment-driven and replaceable.
- Separate local development storage from remote production storage concerns.

## 4. Node Postprocessor Policy

Node postprocessors are first-class quality controls between retrieval and synthesis.

Guidelines:

- Start with simple postprocessors (for example similarity thresholding).
- Add reranking/ordering modules only when evaluation data shows value.
- Prefer minimal chains over opaque stacked logic.
- Keep postprocessor behavior covered by tests using realistic retrieved-node fixtures.

## 5. Memory and Chat History Architecture

### 5.1 Memory Policy

- Prefer the modern `Memory` API for new systems.
- Use stable conversation keys (`session_id` or equivalent) as an explicit contract.
- Keep token limits and truncation behavior documented.

### 5.2 Long-Term Memory

Use long-term memory blocks only when requirements justify added complexity.

- `StaticMemoryBlock` for invariant context.
- `FactExtractionMemoryBlock` for structured recall.
- `VectorMemoryBlock` for retrieval-based historical recall.

### 5.3 Persistence Backends

- Start with in-memory/local development storage when appropriate.
- Move to remote backends (for example async Postgres) for durability and scaling.
- Keep memory backend swaps behind stable interfaces.

### 5.4 Chat Stores

Treat chat stores as persistence primitives for ordered message history.

- Choose backend based on durability, latency, and operations constraints.
- Keep keying strategy and retention policy explicit.

## 6. Structured Output Strategy

Structured outputs should be driven by consumer contracts, not by preference alone.

Use:

- `output_cls` for schema-bound outputs.
- `structured_output_fn` for advanced parsing/validation workflows.

Rules:

- Keep structured contracts versioned and test-covered.
- Do not force structured output for consumers that only need plain text.

## 7. Settings and Configuration Governance

Use `Settings` as a controlled default layer.

Rules:

- Keep global defaults minimal and documented.
- Prefer local overrides for behavior that must remain explicit.
- Avoid hidden global mutations across modules.
- Keep tokenizer, context window, and model settings aligned with runtime model capabilities.

## 8. Observability (Langfuse-Focused)

### 8.1 Instrumentation Baseline

Prefer instrumentation-module workflows over legacy callback-only patterns.

Example baseline:

```python
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

LlamaIndexInstrumentor().instrument()
```

### 8.2 Trace Design

Minimum trace coverage should include:

- Agent lifecycle
- Tool calls and outputs
- Retrieval and synthesis spans
- Error/timeout boundaries for LLM/embedding/vector operations

### 8.3 Langfuse Integration Hygiene

- Keep Langfuse host and key configuration explicit.
- Verify auth/connectivity at startup in controlled environments.
- Keep trace attributes semantically meaningful and stable.

## 9. Integration Patterns (LLM, Embeddings, Vector Store)

### 9.1 LLM + Embedding Providers

- Keep provider/model selection environment-driven.
- Keep request timeout/retry controls explicit.
- Keep embedding and generation models independently configurable.

### 9.2 Vector Store Integrations

- Encapsulate vector-store-specific setup behind storage-context boundaries.
- Preserve retrieval interface stability when switching vector backends.
- Treat metadata filtering as an explicit query policy, not an implicit default.

## 10. Testing, Tooling, and Quality Gates

### 10.1 Test Layers

- Unit tests: deterministic logic and contract validation.
- Integration tests: provider/vector-store wiring and end-to-end query behavior.

### 10.2 Test Reliability Rules

- Keep default unit loop free of external network/services.
- Mark integration/network tests explicitly.
- Test no-match and fallback behavior explicitly.
- Test memory key isolation and session continuity explicitly.

### 10.3 Tooling Discipline

- Use environment-reproducible package workflows.
- Run lint/format/type/test checks as explicit quality gates.
- Keep CI/test commands documented and consistent with local execution.

## 11. Anti-Patterns

- Hidden ingestion on request path or uncontrolled startup side effects.
- Undocumented retrieval defaults.
- Global settings drift causing ingest/query mismatch.
- Premature multi-agent or reranker complexity without evaluation evidence.
- Returning confident answers without sufficient retrieval evidence.

## 12. Adaptation Hook

When applying this universal guide to a specific repository:

1. Define project contracts (API, data schema, session keys, fallback semantics).
2. Choose concrete defaults (retrieval params, memory backend, vector backend).
3. Encode those choices in a project plan/spec separate from this universal document.
4. Keep this file stable; update project-specific decisions in project-specific planning docs.

## 13. References (Covered Scope)

Building Agents:

- https://developers.llamaindex.ai/python/framework/understanding/agent/
- https://developers.llamaindex.ai/python/framework/understanding/agent/streaming/
- https://developers.llamaindex.ai/python/framework/understanding/agent/multi_agent/
- https://developers.llamaindex.ai/python/framework/understanding/agent/structured_output/

Building a RAG pipeline:

- https://developers.llamaindex.ai/python/framework/understanding/rag/indexing/
- https://developers.llamaindex.ai/python/framework/understanding/rag/loading/
- https://developers.llamaindex.ai/python/framework/understanding/rag/querying/
- https://developers.llamaindex.ai/python/framework/understanding/rag/storing/

Deploying:

- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/

Indexing:

- https://developers.llamaindex.ai/python/framework/module_guides/indexing/vector_store_index/

Loading:

- https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/
- https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/transformations/
- https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/

Observability:

- https://developers.llamaindex.ai/python/framework/module_guides/observability/

Querying:

- https://developers.llamaindex.ai/python/framework/module_guides/querying/node_postprocessors/
- https://developers.llamaindex.ai/python/framework/module_guides/querying/node_postprocessors/node_postprocessors/

Storing:

- https://developers.llamaindex.ai/python/framework/module_guides/storing/chat_stores/
- https://developers.llamaindex.ai/python/framework/module_guides/supporting_modules/settings/

Integrations:

- https://developers.llamaindex.ai/python/framework/integrations/embeddings/ollama_embedding/
- https://developers.llamaindex.ai/python/framework/integrations/llm/ollama/
- https://developers.llamaindex.ai/python/framework/integrations/vector_stores/chroma_metadata_filter/
