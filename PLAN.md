# PLAN.md

## Title

Fix Langfuse root `thinking` capture and root `tool_output` rendering

## Why this plan exists

This repository already emits Langfuse traces for chat requests. The current root
trace shape is intentionally optimized for Sessions and Tracing table views:

- root `input`
  - `system_prompt_version`
  - `user_message`
  - `session_id`
- root `output`
  - `answer`
  - `thinking`
  - `tool_calls`

That high-level shape is correct and should stay.

However, there are two quality bugs in the current implementation:

1. `thinking` likely captures only the last emitted thinking fragment instead of
   the full thinking process across the run.
2. `tool_calls[].tool_output` at the root is not the real tool output in a
   readable form. It is currently summarized synthetically for `faq_lookup`
   (`match_count`, `top_faq_id`) instead of showing a shortened real output.

This plan is only about fixing those two issues while preserving the rest of the
Langfuse structure.

## Repository context

Primary implementation file:

- `src/customer_bot/agent/service.py`

Relevant supporting files:

- `src/customer_bot/retrieval/service.py`
- `tests/unit/test_agent_service.py`
- `README.md`

Current facts from the codebase:

- The root Langfuse observation name is `chat_request`.
- The root observation type is `agent`.
- `system_prompt_version` is already set to `"v1"` in root input.
- Root `tool_calls` are already intentionally compact for Session readability.
- Full tool input/output is already captured in nested Langfuse `tool`
  observations.

The FAQ tool returns structured matches with:

- `faq_id`
- `answer`
- `score`

The retrieval layer is deterministic and retrieval-backed fallback behavior must
not change.

## Problem statement

### Problem 1: `thinking` is MAYBE incomplete

In `AgentService._collect_event_data(...)`, the current implementation stores
only one `thinking` string and overwrites it whenever a later `AgentOutput`
event contains another thinking fragment.

That means:

- thinking before a tool call can be lost
- thinking after a tool call can replace earlier thinking
- Langfuse root `output.thinking` may show only the tail of the process rather
  than the full sequence

### Problem 2: root `tool_output` is synthetic instead of real

In the root `tool_calls` summary, `tool_output` is currently transformed into a
compact summary object for FAQ matches, e.g.:

```json
{
  "match_count": 1,
  "top_faq_id": "faq_1"
}
```

That is readable, but it is not the actual tool output. The user expectation is
that the root shows a shortened real result, for example a string derived from
the top FAQ answer, not just counters and IDs. (keep that as in langfuse recommended, build nothing manually when its to complex, keep it simple)

Nested Langfuse tool observations should continue to hold the full structured
output. Only the root summary needs to change.

## Desired end state

Keep the root Langfuse shape exactly as follows:

- root `input`
  - `system_prompt_version`
  - `user_message`
  - `session_id`
- root `output`
  - `answer`
  - `thinking`
  - `tool_calls`

But change the semantics:

- `thinking` must contain the complete captured thinking process across the chat
  request, in chronological order
- `tool_calls[].tool_output` must be a short readable string derived from the
  actual tool result

Do not change:

- API request/response schemas
- no-match fallback behavior
- technical error fallback behavior
- nested tool observation structure
- root `WARNING` / `ERROR` level behavior

## Implementation changes

### 1. Fix `thinking` aggregation in `AgentService`

File:

- `src/customer_bot/agent/service.py`

Current behavior:

- `_collect_event_data(...)` returns a single `thinking: str | None`
- every later thinking fragment overwrites the previous one

Required behavior:

- collect all non-empty thinking fragments emitted during the streamed run
- preserve emission order
- aggregate them into one final root `thinking` string

Detailed rules:

- use a list of strings internally instead of one scalar
- when an `AgentOutput` event contains real thinking, append it
- join fragments at the end with `"\n\n"` between fragments
- remove only exact repeated adjacent fragments if streaming emits duplicates
- if no real thinking fragments are present, final root `thinking` must be `""`

Important:

- do not invent or paraphrase missing thinking
- do not summarize thinking with custom prose
- use only emitted thinking data from the model/agent events

### 2. Keep current root input contract

Do not change `_start_trace_observation(...)` except if required for minor
cleanup.

Root input must remain:

```json
{
  "system_prompt_version": "v1",
  "user_message": "...",
  "session_id": "..."
}
```

### 3. Change root `tool_output` to a real shortened string

File:

- `src/customer_bot/agent/service.py`

Current behavior:

- `_serialize_tool_call(...)` normalizes the real tool output correctly
- `_summarize_tool_call(...)` then compresses it
- `_summarize_tool_output(...)` returns synthetic objects for FAQ matches

Required behavior for root summaries:

- keep `tool_name`
- keep `tool_input`
- keep `is_error`
- change `tool_output` so it becomes a readable string built from the real tool
  output

For `faq_lookup`, the root `tool_output` string must follow this policy:

- if `matches` is empty:
  - use a short no-match string, e.g. `Keine FAQ-Treffer`
- if at least one match exists:
  - show the top match in compact text form
  - include the top FAQ answer text
  - including the `faq_id` prefix is allowed and recommended if it improves
    debugging, e.g. `faq_1: Du kannst ein Konto erstellen, indem du auf
    "Registrieren" klickst und das Formular ausfüllst.`
- if the tool output is already a plain string:
  - use that string, truncated if needed
- if the tool errored:
  - keep a short readable string derived from the error payload or content

Boundaries:

- root string must stay compact and session-friendly
- nested tool observations remain the source of full structured fidelity
- do not dump the whole JSON blob into the root

### 4. Do not change nested tool observations

The existing nested `tool` observations are correct and should remain.

They must still receive:

- full structured tool input
- full structured tool output
- `ERROR` level and status message on tool failures

### 5. Keep status and fallback semantics unchanged

No behavior changes to:

- no-match detection
- tool error detection
- user-facing fallback text
- root `WARNING` for no-match
- root `ERROR` for technical failure

This plan is observability-only.

## Suggested code shape

### In `_collect_event_data(...)`

Refactor return value from:

```python
tuple[str | None, list[dict[str, Any]], bool, bool]
```

to either:

```python
tuple[str, list[dict[str, Any]], bool, bool]
```

or keep the same signature but aggregate internally and return final string.

Recommended internal approach:

1. create `thinking_fragments: list[str] = []`
2. append extracted fragments as events stream in
3. collapse adjacent duplicates
4. join into final string before returning

### In `_summarize_tool_output(...)`

Replace the current FAQ summary-object behavior with string rendering.

Recommended helper behavior:

- dict with `matches: []` -> `"Keine FAQ-Treffer"`
- dict with `matches` and top hit -> string from first hit
- string -> truncated string
- list -> readable count string only if no better representation exists
- unknown dict -> concise stringified/truncated representation

If helpful, introduce a dedicated helper for FAQ root rendering, for example:

```python
def _render_root_tool_output(self, tool_name: str, value: Any) -> str | Any:
    ...
```

This keeps generic summary logic separate from FAQ-specific rendering.

## Acceptance criteria

The change is done when all of the following are true.

### Root input

Langfuse root `input` remains:

```json
{
  "system_prompt_version": "v1",
  "user_message": "...",
  "session_id": "..."
}
```

### Root thinking

For a run where thinking occurs before and after a tool call:

- root `output.thinking` contains both parts
- order is preserved
- earlier fragments are not lost

### Root tool call summary

For a successful FAQ lookup:

- root `tool_calls[0].tool_name == "faq_lookup"`
- root `tool_calls[0].tool_input.question` contains the original tool question
- root `tool_calls[0].tool_output` is a readable string derived from the actual
  top FAQ answer
- root `tool_calls[0].is_error == false`

For a no-match FAQ lookup:

- root `tool_output` is a short readable no-match string

For a tool error:

- root `tool_output` is a short readable error string
- root `is_error == true`

### Nested tool observations

Nested Langfuse `tool` observations still contain the full structured tool
input/output.

### No regressions

These remain unchanged:

- user-facing answers
- no-match fallback behavior
- error fallback behavior
- root warning/error levels

## Tests to add or update

File:

- `tests/unit/test_agent_service.py`

Required test coverage:

1. Thinking aggregation across multiple agent events
   - create at least two `AgentOutput` events with thinking
   - place a `ToolCallResult` between them
   - assert final root `thinking` contains both fragments

2. Root tool output for a matched FAQ
   - assert root `tool_output` is a string
   - assert it contains the top answer text

3. Root tool output for no match
   - assert root `tool_output` is the short no-match string

4. Root tool output for tool error
   - assert root `tool_output` is a readable string
   - assert `is_error` remains true

5. Nested tool observation still stores structured output
   - ensure nested child observation output remains a dict/list structure, not
     the shortened root string

Also update any existing tests that currently assert synthetic FAQ summary
objects in the root.

## Verification commands

Run after implementation:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pytest --collect-only
uv run pytest -m unit
```

If available, also perform one manual Langfuse UI check with a query like:

`Wie kann ich ein Konto erstellen?`

Expected UI outcome:

- root input shows `system_prompt_version`, `user_message`, `session_id`
- root output shows `answer`, full aggregated `thinking`, and root `tool_calls`
- root `tool_output` shows a short real tool-result string
- nested tool span still shows the full structured `matches` payload

## Out of scope

Do not do any of the following in this task:

- redesign prompt text
- change retrieval ranking logic
- add `user_id`
- add new API fields
- remove root `thinking`
- remove root `tool_calls`
- replace nested tool observations

## Default assumptions

- `system_prompt_version` stays `"v1"`
- root `thinking` should remain visible because it is valuable for quick trace
  inspection
- root `tool_calls` should remain visible because they are valuable for
  at-a-glance agent debugging
- the root must stay compact; full fidelity belongs in nested spans
