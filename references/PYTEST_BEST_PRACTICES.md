# PYTEST Best Practices (Universal, Future-Proof)

This document defines long-lived testing standards for Python repositories using `pytest` and `uv`.
It is intentionally repository-agnostic and should remain valid as code structure evolves.

## 1. Core Principles

- Tests are deterministic by default.
- Unit tests are fast, isolated, and do not require network/external services.
- Integration tests are explicit and separately selectable.
- Test failures should explain behavior regressions, not implementation details.
- Favor maintainability over cleverness.

## 2. `uv` Setup for Testing

Use dependency groups for developer/test tooling.

```toml
[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-cov>=5.0",
  "pytest-mock>=3.14",
  "pytest-xdist>=3.6",
]
```

Notes:
- Prefer `[dependency-groups]` over legacy `[tool.uv].dev-dependencies`.
- Keep runtime dependencies separate from dev-only tooling.

Recommended commands:

```bash
uv sync
uv run pytest
uv run pytest -m "not slow and not network"
uv run pytest --maxfail=1 -q
uv run pytest --cov=src --cov-report=term-missing
uv run pytest -n auto
```

## 3. Baseline `pytest` Configuration (`pyproject.toml`)

Use strict defaults to reduce silent test quality regressions:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
  "-ra",
  "--strict-markers",
  "--strict-config",
]
xfail_strict = true
markers = [
  "unit: deterministic tests with no external services",
  "integration: multi-component tests",
  "slow: slower tests excluded from default loops",
  "network: tests requiring network or external endpoints",
]
filterwarnings = [
  "error::DeprecationWarning",
]
```

## 4. Test Suite Architecture (General)

Preferred high-level pattern:

```text
tests/
  conftest.py
  unit/
  integration/
```

Rules:
- Mirror product boundaries with test modules; avoid one giant test file.
- Keep integration tests separate from unit tests.
- Put only broadly reusable fixtures in `tests/conftest.py`.
- Keep narrow fixtures local to test modules.
- Use markers to make selection explicit (`-m unit`, `-m "not slow"`).

## 5. Designing Code to Be Testable

Generate and refactor code with testability as a first-class requirement:

- Depend on interfaces, not hardwired global singletons.
- Inject external collaborators (time, randomness, network clients, filesystem adapters, subprocess runners).
- Keep pure logic separate from side-effectful orchestration.
- Return data structures from core logic; keep I/O at boundaries.
- Avoid hidden global state and implicit environment coupling.
- Minimize mutable shared state; prefer explicit inputs and outputs.
- Keep functions small enough that behavior can be asserted directly.

Practical pattern:
- Pure core: validation, transformations, business rules.
- Impure shell: CLI, file writes, HTTP calls, model calls, process execution.

## 6. Fixtures: Types, Scopes, and When to Use Them

Scope defaults:
- `function` (default): safest; use first.
- `module`: for expensive read-only setup shared in one module.
- `session`: for very expensive stable resources shared suite-wide.

Escalation rule:
- Start at `function`; increase scope only with measurable runtime benefit.

Use `yield` fixtures when teardown is required:

```python
@pytest.fixture
def resource():
    obj = create_resource()
    yield obj
    obj.close()
```

Built-ins to prefer:
- `tmp_path`: per-test temp directories/files.
- `tmp_path_factory`: session-scoped temp artifact creation.
- `monkeypatch`: temporary env/object/module overrides.
- `caplog`: log assertions.
- `capsys` / `capfd`: stdout/stderr assertions.

Prefer `tmp_path` over legacy `tmpdir`.

## 7. Parametrization Best Practices

Use parametrization to encode behavior matrices compactly:

```python
@pytest.mark.parametrize(
    "value,expected",
    [(1, True), (0, False)],
    ids=["positive", "zero"],
)
def test_rule(value, expected):
    ...
```

Guidelines:
- Always provide clear `ids` for readability.
- Use `pytest.param(...)` for per-case marks/metadata.
- Include boundary and failure-mode cases (min/max/empty/invalid).
- Prefer table-driven tests over repetitive one-off functions.

## 8. Mocking and Patching (Critical)

Tool choice matrix:
- `monkeypatch`: lightweight runtime overrides.
- `pytest-mock` (`mocker`): patch lifecycle + call assertions.
- `unittest.mock` (`patch`, `AsyncMock`, `create_autospec`): advanced controls.

Non-negotiable rule:
- Patch where symbols are looked up by the code under test.

Reliability rules:
- Prefer `autospec=True` / `create_autospec(...)` to catch interface drift.
- Use `AsyncMock` for async collaborators.
- Mock boundaries, not internal algorithm steps.
- Assert user-visible outcomes first; avoid brittle micro-assertions.

## 9. Temporary Files and Filesystem Isolation

- Use `tmp_path` for all test-created files and directories.
- Never write to real project output directories in default tests.
- Keep test data local to the test unless shared fixtures clearly reduce duplication.
- Use `--basetemp` only with dedicated directories (pytest clears it per run).

## 10. Plugin Policy (Lean Core + Explicit Expansion)

Recommended core:
- `pytest-cov`
- `pytest-mock`
- `pytest-xdist`

Optional by need:
- `pytest-asyncio` for async-first suites.
- `hypothesis` for property-based testing.
- timeout/flaky plugins for specific reliability problems.

Governance rule:
- Every added plugin must have a concrete use case and an owner.

## 11. Marker and Execution Policy

Minimum marker set:
- `unit`
- `integration`
- `slow`
- `network`

Suggested default loop:

```bash
uv run pytest -m "not slow and not network"
```

Broader validation:

```bash
uv run pytest
```

## 12. Agent Rules for Test Changes

When editing production or test code:

1. Add/adjust tests for changed behavior.
2. Run smallest relevant test subset first.
3. Run linter/formatter after edits:
   - `uv run ruff check --fix .`
   - `uv run ruff format .`
4. Run broader tests when scope is wider or cross-cutting.
5. Keep tests deterministic and isolated by default.

## 13. Anti-Patterns to Avoid

- Hidden network/service calls in default unit tests.
- Overuse of `autouse` fixtures.
- Global mutable state leaks across tests.
- Massive fixtures that bundle unrelated responsibilities.
- Assertions tied to incidental implementation details.
- Marking unstable tests as passing without root-cause follow-up.

## 14. Official References

Pytest:
- https://docs.pytest.org/en/stable/
- https://docs.pytest.org/en/stable/how-to/fixtures.html
- https://docs.pytest.org/en/stable/how-to/parametrize.html
- https://docs.pytest.org/en/stable/how-to/tmp_path.html
- https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- https://docs.pytest.org/en/stable/how-to/mark.html
- https://docs.pytest.org/en/stable/how-to/assert.html
- https://docs.pytest.org/en/stable/how-to/skipping.html
- https://docs.pytest.org/en/stable/how-to/logging.html
- https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html
- https://docs.pytest.org/en/stable/reference/customize.html
- https://docs.pytest.org/en/stable/reference/fixtures.html
- https://docs.pytest.org/en/stable/explanation/goodpractices.html

Mocking:
- https://docs.python.org/3/library/unittest.mock.html
- https://docs.python.org/3/library/unittest.mock-examples.html
- https://pytest-mock.readthedocs.io/en/latest/

`uv`:
- https://docs.astral.sh/uv/
- https://docs.astral.sh/uv/reference/settings/
- https://docs.astral.sh/uv/concepts/projects/config/
- https://docs.astral.sh/uv/concepts/projects/layout/

Plugins:
- https://pytest-cov.readthedocs.io/en/latest/
- https://pytest-xdist.readthedocs.io/en/latest/
- https://pytest-asyncio.readthedocs.io/en/stable/

## 15. Definition of Done for Pytest Work

A testing-related change is complete when:

1. Relevant behavior is covered by deterministic tests.
2. Fixtures are scoped intentionally and cleaned up safely.
3. Patching follows lookup-location rules and avoids brittle internals.
4. `uv` commands and project test config remain coherent.
5. Lint/format and relevant test commands were executed for changed scope.
