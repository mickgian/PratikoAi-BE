# RAG STEP 130 — CacheService.invalidate_faq by id or signature (RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature)

**Type:** process  
**Category:** preflight  
**Node ID:** `InvalidateFAQCache`

## Intent (Blueprint)
Invalidates cached FAQ responses when an FAQ is published or updated. When an FAQ entry is created or modified (from Step 129), this step clears related cache entries by FAQ ID and content signature to ensure fresh data is served. This step is derived from the Mermaid node: `InvalidateFAQCache` (CacheService.invalidate_faq by id or signature).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/preflight.py:step_130__invalidate_faqcache`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that invalidates cached FAQ entries. Uses cache_service.clear_cache() to remove cached responses by FAQ ID patterns. Creates cache invalidation metadata for tracking. Preserves all context data. Routes to 'vector_reindex' (Step 131) per Mermaid flow.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing service behavior

## TDD Task List
- [x] Unit tests (invalidate by FAQ ID, multiple patterns, signature invalidation, context preservation, metadata tracking, no cache entries, error handling, logging)
- [x] Parity tests (cache invalidation behavior verification)
- [x] Integration tests (PublishGolden→InvalidateFAQCache flow, FAQ publication completion)
- [x] Implementation changes (async orchestrator wrapping cache_service)
- [x] Observability: add structured log line
  `RAG STEP 130 (RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature): CacheService.invalidate_faq by id or signature | attrs={faq_id, keys_deleted, operation, processing_stage}`
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
- app/orchestrators/preflight.py:761 — step_130__invalidate_faqcache (async orchestrator)
- tests/test_rag_step_130_invalidate_faq_cache.py — 11 comprehensive tests (all passing)

Key Features:
- Async orchestrator invalidating FAQ-related cache entries
- Uses cache_service.clear_cache() with FAQ ID patterns
- Handles both ID-based and signature-based cache invalidation
- Structured logging with rag_step_log (step 130, processing stages)
- Context preservation (expert_id, trust_score, user/session data)
- Cache invalidation metadata tracking (invalidated_at, faq_id, operation, success)
- Error handling with graceful degradation
- Routes to 'vector_reindex' (Step 131) per Mermaid flow

Test Coverage:
- Unit: invalidate by FAQ ID, multiple patterns, signature invalidation, context preservation, metadata tracking, no cache entries, error handling, logging
- Parity: cache invalidation behavior verification
- Integration: PublishGolden→InvalidateFAQCache flow

Operations:
- Cache invalidation: uses cache_service.clear_cache(pattern=f"faq_var:*{faq_id}*")
- Metadata: tracks keys_deleted, invalidation timestamp, success status
- Error: sets error in cache_invalidation → success=False

Notes:
- Full implementation complete following MASTER_GUARDRAILS
- Thin orchestrator pattern (no business logic)
- All TDD tasks completed
<!-- AUTO-AUDIT:END -->