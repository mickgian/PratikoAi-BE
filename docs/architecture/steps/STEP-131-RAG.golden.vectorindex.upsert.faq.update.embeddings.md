# RAG STEP 131 — VectorIndex.upsert_faq update embeddings (RAG.golden.vectorindex.upsert.faq.update.embeddings)

**Type:** process  
**Category:** golden  
**Node ID:** `VectorReindex`

## Intent (Blueprint)
Updates vector embeddings for published/updated FAQ entries in the vector index. When an FAQ is created or modified (from Step 129), this step processes FAQ content and metadata to create/update vector embeddings using EmbeddingManager. Runs in parallel with InvalidateFAQCache (Step 130) to complete the FAQ publication flow. This step is derived from the Mermaid node: `VectorReindex` (VectorIndex.upsert_faq update embeddings).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_131__vector_reindex`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that updates vector embeddings for FAQ entries. Uses EmbeddingManager.update_pinecone_embeddings to upsert FAQ content and metadata into Pinecone vector index. Creates vector indexing metadata for observability. Preserves all context data. Runs in parallel with Step 130 from Step 129 per Mermaid flow.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing service behavior

## TDD Task List
- [x] Unit tests (update FAQ embeddings, handle updated FAQs, context preservation, metadata inclusion, error handling, indexing metadata, completion flow, logging)
- [x] Parity tests (embedding update behavior verification)
- [x] Integration tests (PublishGolden→VectorReindex flow, parallel execution with Step 130)
- [x] Implementation changes (async orchestrator wrapping EmbeddingManager)
- [x] Observability: add structured log line
  `RAG STEP 131 (RAG.golden.vectorindex.upsert.faq.update.embeddings): VectorIndex.upsert_faq update embeddings | attrs={faq_id, embeddings_updated, version, operation, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing service)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ✅  |  Confidence: 1.00

Implementation:
- app/orchestrators/golden.py:972 — step_131__vector_reindex (async orchestrator)
- tests/test_rag_step_131_vector_reindex.py — 11 comprehensive tests (all passing)

Key Features:
- Async orchestrator updating FAQ vector embeddings
- Uses EmbeddingManager.update_pinecone_embeddings for vector operations
- Combines FAQ question+answer content for embedding
- Rich metadata inclusion (category, version, regulatory refs, quality score)
- Structured logging with rag_step_log (step 131, processing stages)
- Context preservation (expert_id, trust_score, user/session data)
- Vector index metadata tracking (embeddings_updated, processing_time, success)
- Error handling with graceful degradation
- Runs in parallel with Step 130 from Step 129 per Mermaid flow

Test Coverage:
- Unit: FAQ embedding updates, version handling, context preservation, metadata inclusion, error handling, indexing metadata, completion flow, logging
- Parity: embedding update behavior verification
- Integration: PublishGolden→VectorReindex flow, parallel execution with Step 130

Operations:
- Vector update: uses EmbeddingManager.update_pinecone_embeddings with FAQ content
- Metadata: tracks embeddings_updated, processing_time, version, operation, success
- Error: sets error in vector_index_metadata → success=False

Notes:
- Full implementation complete following MASTER_GUARDRAILS
- Thin orchestrator pattern (no business logic)
- All TDD tasks completed
- Parallel execution with Step 130 as per Mermaid diagram
<!-- AUTO-AUDIT:END -->