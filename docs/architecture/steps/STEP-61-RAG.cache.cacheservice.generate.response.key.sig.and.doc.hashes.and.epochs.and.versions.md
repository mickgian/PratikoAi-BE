# RAG STEP 61 — CacheService._generate_response_key sig and doc_hashes and epochs and versions (RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions)

**Type:** process  
**Category:** cache  
**Node ID:** `GenHash`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GenHash` (CacheService._generate_response_key sig and doc_hashes and epochs and versions).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/cache.py:131` - `step_61__gen_hash()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator generating comprehensive cache key from query signature, document hashes, knowledge epochs, and system versions. Creates deterministic hash for Redis cache storage and retrieval. Routes to Step 62 (CacheHit) for lookup.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing caching infrastructure

## TDD Task List
- [x] Unit tests (caching operations, invalidation, key generation)
- [x] Integration tests (cache flow and invalidation handling)
- [x] Implementation changes (async orchestrator with caching operations, invalidation, key generation)
- [x] Observability: add structured log line
  `RAG STEP 61 (...): ... | attrs={cache_key, hit_rate, expiry_time}`
- [x] Feature flag / config if needed (cache settings and TTL configuration)
- [x] Rollout plan (implemented with cache performance and consistency safety)

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