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
Status: 🔌  |  Confidence: 0.53

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.53)
   Evidence: Score 0.53, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.53)
   Evidence: Score 0.53, Publish an approved FAQ to make it available to users
3) app/api/v1/faq.py:431 — app.api.v1.faq.update_faq (score 0.52)
   Evidence: Score 0.52, Update an existing FAQ entry with versioning.

Requires admin privileges.
4) app/orchestrators/golden.py:534 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
5) app/orchestrators/golden.py:972 — app.orchestrators.golden.step_131__vector_reindex (score 0.50)
   Evidence: Score 0.50, RAG STEP 131 — VectorIndex.upsert_faq update embeddings
ID: RAG.golden.vectorind...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->