---
name: pytest
description: Plan, write, review, and debug Python tests with pytest in a deterministic, maintainable, and reproducible way. Use when adding tests, changing behavior with test impact, reviewing test quality, fixing flaky tests, or diagnosing failing pytest runs.
---

# Pytest

This skill provides a universal pytest workflow that is not tied to any specific repository layout, marker set, or command wrapper.

## Core Principles

Follow these principles for all pytest work:

1. Deterministic by default: avoid hidden network/time/random dependencies in standard test loops.
2. Fast feedback first: run the smallest relevant test subset before broader suites.
3. Behavior over implementation: assert externally visible behavior instead of brittle internals.
4. Isolate side effects: keep filesystem, env, subprocess, and network effects explicit and mockable.
5. Clear failure reports: provide reproducible commands and exact failing assertions/errors.

## When To Use This Skill

Use this skill when:

- creating or updating tests for changed behavior
- reviewing tests for reliability, isolation, and maintainability
- debugging failing or flaky pytest runs
- choosing fixture scope, mocking strategy, or parametrization structure
- defining a safe escalation path from local tests to broader validation

## Default Workflow

1. Determine test impact from the change:
   - unit-level logic only
   - integration boundary touched
   - cross-cutting/systemic behavior touched
2. Run the smallest relevant tests first (single test/module/marker selection).
3. Fix failures with root-cause focus before widening scope.
4. Escalate to broader suites once local target tests pass.
5. Report what ran, what failed/passed, and remaining risks or untested areas.

## Test Design Guidelines

- Prefer table-driven parametrization with explicit `ids`.
- Keep fixtures small and purpose-specific; default to function scope.
- Use `tmp_path` for filesystem isolation.
- Inject or patch boundaries (time, randomness, HTTP, DB, subprocess), not algorithm internals.
- Patch where symbols are looked up by the code under test.
- Prefer autospecced mocks when possible to detect interface drift.
- Use `AsyncMock` for async collaborators.

## Flaky Test Triage Flow

1. Confirm reproducibility and collect the minimal failing command.
2. Classify likely source:
   - ordering/state leakage
   - timing/concurrency
   - external dependency instability
   - non-deterministic assertions
3. Stabilize by isolating shared mutable state and hard dependencies.
4. Add or improve assertions to validate intended behavior deterministically.
5. Document residual risk if flake cannot be eliminated immediately.

## Anti-Patterns

- hidden network calls in default unit runs
- broad `autouse` fixtures that hide coupling
- assertions on incidental call order/details without user-visible value
- oversized fixtures bundling unrelated setup concerns
- marking unstable tests as effectively ignored without root-cause follow-up

## Adaptation Hook

If a repository provides local rules (for example `AGENTS.md`, testing docs, or CI policies), apply this skill as the base and then prioritize local repository rules where they are more specific.

## References

- universal pytest practices: `PYTEST_BEST_PRACTICES.md` (if present in the repo)
- deeper workflow guides:
  - `references/test-design.md`
  - `references/test-execution.md`
  - `references/failure-triage.md`
