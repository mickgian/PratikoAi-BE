# RAG STEP 66 — Return cached response (RAG.cache.return.cached.response)

**Type:** process  
**Category:** cache  
**Node ID:** `ReturnCached`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReturnCached` (Return cached response).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/cache.py:654` - `step_66__return_cached()`
- **Status:** 🔌
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_66
- Incoming edges: [62]
- Outgoing edges: none

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->