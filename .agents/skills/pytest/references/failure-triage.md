# Failure Triage

When pytest fails, triage in this order:

1. Reproduce with the smallest command.
2. Capture exact failure data:
   - assertion diff
   - exception type and message
   - stack location
3. Identify failure class:
   - product behavior regression
   - test bug/invalid expectation
   - environment/config mismatch
   - flakiness/non-determinism
4. Apply minimal fix and rerun the same command.
5. Escalate to a broader suite only after targeted pass.

Reporting template:

- command used
- failing tests
- root cause summary
- change made
- verification commands and outcomes
- remaining risks (if any)
