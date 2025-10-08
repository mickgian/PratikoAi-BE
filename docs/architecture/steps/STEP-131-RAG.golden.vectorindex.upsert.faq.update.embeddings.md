# RAG STEP 131 — VectorIndex.upsert_faq update embeddings (RAG.golden.vectorindex.upsert.faq.update.embeddings)

**Type:** process  
**Category:** golden  
**Node ID:** `VectorReindex`

## Intent (Blueprint)
Updates vector embeddings for published/updated FAQ entries in the vector index. When an FAQ is created or modified (from Step 129), this step processes FAQ content and metadata to create/update vector embeddings using EmbeddingManager. Runs in parallel with InvalidateFAQCache (Step 130) to complete the FAQ publication flow. This step is derived from the Mermaid node: `VectorReindex` (VectorIndex.upsert_faq update embeddings).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:step_131__vector_reindex`
- **Status:** 🔌
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
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->