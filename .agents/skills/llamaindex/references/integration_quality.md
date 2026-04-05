# Integration and Quality Patterns

## FastAPI Integration

- Keep endpoint handlers thin and typed.
- Move LlamaIndex orchestration into service layers.
- Inject runtime dependencies instead of hardcoding global singletons.

## Langfuse Integration

- Keep host and credential configuration explicit.
- Validate connectivity in controlled startup checks.
- Ensure traces include enough context to debug retrieval/tool decisions.

## Provider Integrations (LLM/Embedding/Vector)

- Keep provider selection environment-driven.
- Keep timeout/retry behavior explicit.
- Keep ingest-time and query-time embedding settings aligned.

## Testing

- Keep unit tests deterministic and isolated.
- Mark integration/network tests explicitly.
- Validate fallback and no-match behavior with dedicated tests.

## Tooling

- Use `uv` for reproducible dependency/command workflows.
- Keep `ruff` lint/format checks in the default development loop.
- Keep CI and local test commands aligned.
