# RAG STEP 130 — CacheService.invalidate_faq by id or signature (RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature)

**Type:** process  
**Category:** preflight  
**Node ID:** `InvalidateFAQCache`

## Intent (Blueprint)
Invalidates cached FAQ responses when an FAQ is published or updated. When an FAQ entry is created or modified (from Step 129), this step clears related cache entries by FAQ ID and content signature to ensure fresh data is served. This step is derived from the Mermaid node: `InvalidateFAQCache` (CacheService.invalidate_faq by id or signature).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/preflight.py:909` - `step_130__invalidate_faqcache()`
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
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/services/cache.py:30 — app.services.cache.CacheService.__init__ (score 0.29)
   Evidence: Score 0.29, Initialize the cache service.
2) app/core/decorators/cache.py:304 — app.core.decorators.cache.invalidate_cache_on_update (score 0.28)
   Evidence: Score 0.28, Decorator to invalidate cache entries when data is updated.

Args:
    cache_key...
3) app/models/faq.py:486 — app.models.faq.generate_faq_cache_key (score 0.28)
   Evidence: Score 0.28, Generate cache key for FAQ variations.
4) app/orchestrators/preflight.py:909 — app.orchestrators.preflight.step_130__invalidate_faqcache (score 0.28)
   Evidence: Score 0.28, RAG STEP 130 — CacheService.invalidate_faq by id or signature
ID: RAG.preflight....
5) app/services/cache.py:82 — app.services.cache.CacheService._generate_query_hash (score 0.28)
   Evidence: Score 0.28, Generate a deterministic hash for query deduplication.

Args:
    messages: List...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for InvalidateFAQCache
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->