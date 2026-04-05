# Test Execution

Run tests in progressive loops:

1. Smallest loop:
   - single test function
   - single test module
2. Targeted loop:
   - related package/subtree
   - marker-based subset if markers are available
3. Broader loop:
   - default suite for the repository
   - full suite when change is cross-cutting

Execution notes:

- Keep commands reproducible and copy-ready in reports.
- Prefer deterministic local loops before parallelizing.
- Expand scope only after lower-level failures are resolved.
