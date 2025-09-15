# RAG STEP 66 — Return cached response (RAG.cache.return.cached.response)

**Type:** process  
**Category:** cache  
**Node ID:** `ReturnCached`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReturnCached` (Return cached response).

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
  `RAG STEP 66 (RAG.cache.return.cached.response): Return cached response | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.52

Top candidates:
1) app/core/decorators/cache.py:19 — app.core.decorators.cache.cache_llm_response (score 0.52)
   Evidence: Score 0.52, Decorator to cache LLM responses based on messages and model.

Args:
    ttl: Ti...
2) app/core/decorators/cache.py:112 — app.core.decorators.cache.cache_conversation (score 0.52)
   Evidence: Score 0.52, Decorator to cache conversation history.

Args:
    ttl: Time to live in seconds...
3) app/core/decorators/cache.py:190 — app.core.decorators.cache.cache_result (score 0.52)
   Evidence: Score 0.52, Generic caching decorator for any function result.

Args:
    key_func: Function...
4) app/core/decorators/cache.py:304 — app.core.decorators.cache.invalidate_cache_on_update (score 0.52)
   Evidence: Score 0.52, Decorator to invalidate cache entries when data is updated.

Args:
    cache_key...
5) app/services/cache.py:30 — app.services.cache.CacheService.__init__ (score 0.52)
   Evidence: Score 0.52, Initialize the cache service.

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Add cache invalidation and TTL tests
<!-- AUTO-AUDIT:END -->