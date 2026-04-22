# Guardrails AI Hub Notes

This file is a reconstructed working summary of the Guardrails Hub content that was previously present in this repository.
It is not guaranteed to be byte-identical to the deleted original file.
It intentionally contains only the PII detector information requested by the user.

## Detect PII

Summary:

- Detects personally identifiable information in text
- Uses Microsoft Presidio under the hood
- Can be used for input and output validation
- Can fail, noop, or return a fixed anonymized value depending on `on_fail`

## Intended Use

This validator checks whether text contains configured PII entity types.
If configured with a fixing action, it can anonymize the text rather than just fail.

## Installation

```bash
guardrails hub install hub://guardrails/detect_pii
```

## Import Pattern

```python
from guardrails import Guard
from guardrails.hub import DetectPII
```

## Basic Usage

```python
from guardrails import Guard
from guardrails.hub import DetectPII

guard = Guard().use(
    DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER"], on_fail="exception")
)

guard.validate("Hello world")
```

## Input Validation Example

```python
from guardrails import Guard
from guardrails.hub import DetectPII

guard = Guard().use(
    DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER"], on_fail="exception"),
    on="messages",
)
```

## `on_fail` Notes

Relevant behaviors:

- `exception`
  - fail validation and raise
- `noop`
  - log but keep original text
- `fix`
  - return anonymized text if supported
- `reask`
  - ask the model to regenerate compliant text
- custom function
  - possible, but not the project default

## Important Project Notes

For this repository:

- input-side sensitive PII/secrets should block before any other LLM-based guard runs
- output-side PII detection should be reused for final answer validation
- do not rely on blind anonymization for secrets like API keys
- augment `DetectPII` with custom secret/token pattern checks

## Constructor Notes

The docs described this validator roughly as:

```python
DetectPII(pii_entities=..., on_fail="noop")
```

Parameters:

- `pii_entities`
  - string or list of entity names
- `on_fail`
  - one of the standard Guardrails fail behaviors

## Metadata Notes

`pii_entities` can also be supplied or overridden via metadata at validation time.

That is useful if the application wants env-driven dynamic entity lists.

## Why This Validator Matters for This Project

This project needs:

- configurable env-driven PII entity lists
- hard blocking before forwarding content to downstream guards or LLM providers
- reuse of the same detection family on outputs

That makes `DetectPII` a good base component for:

- `SecretPIIGuard`
- `OutputSensitiveDataGuard`

## Project Guidance

Use `DetectPII` as the hub validator base, but do not treat it as sufficient by itself for secret handling.

Add project-local heuristics or regex checks for:

- API keys
- bearer tokens
- secret-like credentials
- similar high-risk values not reliably covered by generic PII detection
