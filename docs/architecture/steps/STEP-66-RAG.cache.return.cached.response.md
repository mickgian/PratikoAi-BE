# RAG STEP 66 — Return cached response (RAG.cache.return.cached.response)

**Type:** process  
**Category:** cache  
**Node ID:** `ReturnCached`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReturnCached` (Return cached response).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/cache.py:654` - `step_66__return_cached()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator returning cached response to avoid redundant LLM calls. Optimizes performance by serving previously computed results.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing caching infrastructure

## TDD Task List
- [x] Unit tests (caching operations, invalidation, key generation)
- [x] Integration tests (cache flow and invalidation handling)
- [x] Implementation changes (async orchestrator with caching operations, invalidation, key generation)
- [x] Observability: add structured log line
  `RAG STEP 66 (...): ... | attrs={cache_key, hit_rate, expiry_time}`
- [x] Feature flag / config if needed (cache settings and TTL configuration)
- [x] Rollout plan (implemented with cache performance and consistency safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.66

Top candidates:
1) app/orchestrators/cache.py:774 — app.orchestrators.cache.step_68__cache_response (score 0.66)
   Evidence: Score 0.66, RAG STEP 68 — CacheService.cache_response Store in Redis
ID: RAG.cache.cacheserv...
2) app/services/cache.py:567 — app.services.cache.get_redis_client (score 0.66)
   Evidence: Score 0.66, Get Redis client from the global cache service.

Returns:
    Redis client insta...
3) app/orchestrators/cache.py:283 — app.orchestrators.cache.step_62__cache_hit (score 0.62)
   Evidence: Score 0.62, RAG STEP 62 — Cache hit?
ID: RAG.cache.cache.hit
Type: decision | Category: cach...
4) app/orchestrators/cache.py:654 — app.orchestrators.cache.step_66__return_cached (score 0.58)
   Evidence: Score 0.58, RAG STEP 66 — Return cached response
ID: RAG.cache.return.cached.response
Type: ...
5) app/core/decorators/cache.py:19 — app.core.decorators.cache.cache_llm_response (score 0.53)
   Evidence: Score 0.53, Decorator to cache LLM responses based on messages and model.

Args:
    ttl: Ti...

Notes:
- Implementation exists but may not be wired correctly
- Detected Node but not in runtime registry

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Add cache invalidation and TTL tests
<!-- AUTO-AUDIT:END -->