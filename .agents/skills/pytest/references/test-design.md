# Test Design

Use this checklist when creating or refactoring tests:

1. Define the behavior under test in one sentence.
2. Cover at least one happy path, one boundary, and one failure mode.
3. Keep setup minimal and local to the test unless reuse is clearly beneficial.
4. Use parametrization for behavior matrices; include readable case IDs.
5. Avoid coupling assertions to implementation details that can change without breaking behavior.

Design heuristics:

- Prefer pure-function coverage first, then orchestration paths.
- Keep one dominant reason to fail per test.
- Favor explicit inputs/outputs over implicit global context.
