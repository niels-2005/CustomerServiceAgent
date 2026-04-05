# RAG Pipeline Patterns

## Loading and Validation

- Use source-specific loaders with explicit schema validation.
- Validate required fields before node creation.
- Keep ingestion failure messages actionable.

## Transformations and Node Parsing

- Add transformations only when they materially improve retrieval quality.
- Match node granularity to source semantics.
- Avoid unnecessary chunking for already atomic records.

## Indexing and Storage

- Use `VectorStoreIndex` for semantic retrieval workloads.
- Keep embedding model parity between ingest and query.
- Persist index/vector-store state to avoid repeated expensive rebuilds.

## Querying Flow

Treat querying as explicit stages:

1. Retrieval
2. Postprocessing
3. Response synthesis

## Node Postprocessors

- Start with minimal postprocessing (for example similarity thresholding).
- Add rerankers/orderers only after evaluation shows measurable benefit.
- Keep postprocessor chains explainable and test-covered.

## Fallback Policy

- Define explicit behavior for low-confidence or empty retrieval results.
- Prefer safe fallback responses over speculative answers.
