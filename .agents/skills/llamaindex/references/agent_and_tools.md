# Agent and Tool Patterns

## Agent Pattern Choice

Use the minimum viable pattern:

- Single-agent tool calling for focused workflows.
- Multi-agent orchestration when specialist separation is required.
- Custom planner loops only for strict control-flow requirements.

## Tool Interface Rules

- Tool names must be stable and semantically specific.
- Tool docstrings should state purpose, expected input, and output semantics.
- Keep tool signatures typed and minimal.
- Keep side effects explicit and traceable.

## Streaming and Control

- Use streaming events for long-running agent workflows.
- Use `return_direct` when a tool response should terminate loop execution.
- Capture tool call args/results in traces to support incident/debug workflows.

## Structured Output

Use structured output only when consumers need a schema contract:

- `output_cls` for direct schema-driven responses.
- `structured_output_fn` for custom post-processing/validation pipelines.
