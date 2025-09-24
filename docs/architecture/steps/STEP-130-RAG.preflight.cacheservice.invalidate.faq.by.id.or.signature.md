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
4) app/orchestrators/preflight.py:761 — app.orchestrators.preflight.step_130__invalidate_faqcache (score 0.28)
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