# RAG STEP 39 — KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost (RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost)

**Type:** process  
**Category:** preflight  
**Node ID:** `KBPreFetch`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBPreFetch` (KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost).

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
  `RAG STEP 39 (RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost): KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.27

Top candidates:
1) load_testing/locust_tests.py:215 — load_testing.locust_tests.PratikoAIUser.knowledge_search (score 0.27)
   Evidence: Score 0.27, Test regulatory knowledge searches
2) app/core/decorators/cache.py:19 — app.core.decorators.cache.cache_llm_response (score 0.23)
   Evidence: Score 0.23, Decorator to cache LLM responses based on messages and model.

Args:
    ttl: Ti...
3) app/core/decorators/cache.py:112 — app.core.decorators.cache.cache_conversation (score 0.23)
   Evidence: Score 0.23, Decorator to cache conversation history.

Args:
    ttl: Time to live in seconds...
4) app/core/decorators/cache.py:190 — app.core.decorators.cache.cache_result (score 0.23)
   Evidence: Score 0.23, Generic caching decorator for any function result.

Args:
    key_func: Function...
5) app/core/decorators/cache.py:304 — app.core.decorators.cache.invalidate_cache_on_update (score 0.23)
   Evidence: Score 0.23, Decorator to invalidate cache entries when data is updated.

Args:
    cache_key...

Notes:
- Weak or missing implementation
- Top match is in test files
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for KBPreFetch
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->