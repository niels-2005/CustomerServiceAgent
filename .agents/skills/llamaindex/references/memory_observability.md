# Memory and Observability Patterns

## Memory Strategy

- Use explicit conversation keys (`session_id` or equivalent).
- Document token limits and truncation policy.
- Start with simple memory where appropriate; add long-term blocks only when justified.

## Long-Term Memory Blocks

Use selectively:

- `StaticMemoryBlock` for invariant context
- `FactExtractionMemoryBlock` for extracted facts
- `VectorMemoryBlock` for retrieval-based historical recall

## Chat Store Strategy

- Select chat-store backend based on durability, latency, and operations constraints.
- Keep retention and keying policies explicit.
- Keep backend swappable behind stable interfaces.

## Observability Baseline

Prefer instrumentation-module tracing and explicit provider integration.

Langfuse-focused baseline:

```python
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

LlamaIndexInstrumentor().instrument()
```

## Trace Coverage

Capture at least:

- agent lifecycle
- tool calls and outputs
- retrieval and synthesis spans
- errors and timeout boundaries
