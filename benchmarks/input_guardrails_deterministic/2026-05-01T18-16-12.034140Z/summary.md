# Benchmark 1 Summary

## Overview

| Field | Value |
| --- | --- |
| Benchmark | `input_guardrails_deterministic` |
| Dataset | `datasets/benchmark/input_guardrails_deterministic.csv` |
| Run Slug | `2026-05-01T18-16-12.034140Z` |
| Total Cases | 10 |
| Passed Cases | 10 |
| Failed Cases | 0 |
| Pass Rate | 100.00% |
| Error Count | 0 |

## Performance

| Metric | Value |
| --- | --- |
| Avg Latency | 1.086 s |
| P50 Latency | 1.001 s |
| P90 Latency | 2.194 s |

## Cost

| Metric | Value |
| --- | --- |
| Avg Price | 0.000244 € |
| Total Costs | 0.002439 € |
| Price Enrichment | resolved |

## Guardrail Metrics

| Metric | Actual Count | Expected Count | Actual Rate | Expected Rate |
| --- | --- | --- | --- | --- |
| PII | 5 | 5 | 50.00% | 50.00% |
| Prompt Injection | 1 | 1 | 10.00% | 10.00% |
| Off Topic | 2 | 2 | 20.00% | 20.00% |
| Escalation | 1 | 1 | 10.00% | 10.00% |
