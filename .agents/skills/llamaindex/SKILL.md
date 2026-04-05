---
name: llamaindex
description: Universal LlamaIndex architecture and implementation guidance for agents, tools, RAG pipelines, memory, observability, and integrations. Use when planning, building, refactoring, or reviewing LlamaIndex-based systems, including FastAPI service integration, Ollama-based model setups, Chroma-backed retrieval, Langfuse tracing, and test/tooling quality gates.
---

# LlamaIndex

This skill provides universal, non-versioned guidance for building and maintaining LlamaIndex applications.

## Core Principles

1. Start with the simplest architecture that satisfies requirements.
2. Keep data contracts and retrieval behavior explicit.
3. Separate ingestion/indexing from serving paths.
4. Make observability first-class, not optional.
5. Keep runtime/provider choices configurable and test-covered.

## Standard Workflow

1. Define architecture mode: single agent, multi-agent, or custom planner.
2. Define source data contracts and ingestion boundaries.
3. Implement retrieval pipeline with explicit retriever/postprocessor/synthesizer choices.
4. Add tools and agent orchestration with clear tool schemas and deterministic behavior.
5. Add memory/session strategy and chat-store persistence strategy.
6. Instrument tracing (Langfuse-focused in this repo) before broad rollout.
7. Lock quality gates with lint/format/test execution.

## Integration Rules (Concise)

- FastAPI: keep handlers thin, move orchestration into services, keep request/response models typed.
- Langfuse: prefer instrumentation-module paths and explicit env configuration.
- pytest: keep unit tests deterministic; mark integration/network tests explicitly.
- uv: keep dependency and command workflows reproducible.
- ruff: enforce lint/format gates in local + CI loops.

## Source of Truth and References

Use `LLAMAINDEX_BEST_PRACTICES.md` in this repository as the canonical universal rule set.

Load focused references as needed:

- `references/agent_and_tools.md`
- `references/rag_pipeline.md`
- `references/memory_observability.md`
- `references/integration_quality.md`

## Anti-Patterns

- Coupling ingest/index rebuilds to every API request.
- Adding multi-agent complexity before proving single-agent limits.
- Relying on hidden defaults for retrieval or memory behavior.
- Returning confident answers without sufficient retrieval evidence.
- Shipping without trace visibility across tool/retrieval boundaries.
