# Benchmark 1 Summary

## Overview

| Field | Value |
| --- | --- |
| Benchmark | `benchmark_1_input_guardrails_deterministic` |
| Dataset | `datasets/benchmark/benchmark_1_input_guardrails_deterministic.json` |
| Run Slug | `2026-05-01T21-21` |
| Total Cases | 10 |
| Passed Cases | 10 |
| Failed Cases | 0 |
| Pass Rate | 100.00% |
| Error Count | 0 |

## Performance

| Metric | Value |
| --- | --- |
| Avg Latency | 1.222 s |
| P50 Latency | 0.945 s |
| P90 Latency | 3.083 s |

## Cost

| Metric | Value |
| --- | --- |
| Avg Price | 0.000266 € |
| Total Costs | 0.002390 € |
| Price Enrichment | resolved |

## Guardrail Metrics

| Metric | Actual Count | Expected Count | Actual Rate | Expected Rate |
| --- | --- | --- | --- | --- |
| PII | 5 | 5 | 50.00% | 50.00% |
| Prompt Injection | 1 | 1 | 10.00% | 10.00% |
| Off Topic | 2 | 2 | 20.00% | 20.00% |
| Escalation | 1 | 1 | 10.00% | 10.00% |
