# RAG STEP 130 — CacheService.invalidate_faq by id or signature (RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature)

**Type:** process
**Category:** preflight
**Node ID:** `InvalidateFAQCache`

## Intent (Blueprint)
Invalidates cached FAQ responses when an FAQ is published or updated. When an FAQ entry is created or modified (from Step 129), this step clears related cache entries by FAQ ID and content signature to ensure fresh data is served. This step is derived from the Mermaid node: `InvalidateFAQCache` (CacheService.invalidate_faq by id or signature).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/preflight.py:909` - `step_130__invalidate_faqcache()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator that invalidates cached FAQ entries. Uses cache_service.clear_cache() to remove cached responses by FAQ ID patterns. Creates cache invalidation metadata for tracking. Preserves all context data. Runs in parallel with Step 129 (PublishGolden) per Mermaid flow.

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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->
