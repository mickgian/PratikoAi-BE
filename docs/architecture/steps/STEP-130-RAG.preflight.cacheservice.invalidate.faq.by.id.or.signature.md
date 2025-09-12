# RAG STEP 130 — CacheService.invalidate_faq by id or signature (RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature)

**Type:** process  
**Category:** preflight  
**Node ID:** `InvalidateFAQCache`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `InvalidateFAQCache` (CacheService.invalidate_faq by id or signature).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 130 (RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature): CacheService.invalidate_faq by id or signature | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.30

Top candidates:
1) app/services/cache.py:30 — app.services.cache.CacheService.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the cache service.
2) app/services/cache.py:82 — app.services.cache.CacheService._generate_query_hash (score 0.30)
   Evidence: Score 0.30, Generate a deterministic hash for query deduplication.

Args:
    messages: List...
3) app/services/cache.py:107 — app.services.cache.CacheService._generate_conversation_key (score 0.30)
   Evidence: Score 0.30, Generate cache key for conversation history.

Args:
    session_id: Unique sessi...
4) app/services/cache.py:118 — app.services.cache.CacheService._generate_query_key (score 0.30)
   Evidence: Score 0.30, Generate cache key for LLM query response.

Args:
    query_hash: Hash of the qu...
5) app/services/cache.py:27 — app.services.cache.CacheService (score 0.27)
   Evidence: Score 0.27, Redis-based caching service for LLM responses and conversations.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->