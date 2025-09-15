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
Status: 🔌  |  Confidence: 0.35

Top candidates:
1) app/ragsteps/preflight/step_39_rag_preflight_knowledgesearch_retrieve_topk_bm25_and_vectors_and_recency_boost.py:39 — app.ragsteps.preflight.step_39_rag_preflight_knowledgesearch_retrieve_topk_bm25_and_vectors_and_recency_boost.step_39_rag_preflight_knowledgesearch_retrieve_topk_bm25_and_vectors_and_recency_boost (score 0.35)
   Evidence: Score 0.35, Token-rich adapter function for STEP 39 (KBPreFetch).
Minimal, side-effect-free;...
2) app/ragsteps/preflight/step_39_rag_preflight_knowledgesearch_retrieve_topk_bm25_and_vectors_and_recency_boost.py:63 — app.ragsteps.preflight.step_39_rag_preflight_knowledgesearch_retrieve_topk_bm25_and_vectors_and_recency_boost.run (score 0.34)
   Evidence: Score 0.34, Backward-compatible entrypoint that delegates to the token-rich function.
3) app/services/knowledge_search_service.py:442 — app.services.knowledge_search_service.KnowledgeSearchService._calculate_recency_boost (score 0.30)
   Evidence: Score 0.30, Calculate recency boost based on document age.
4) app/services/hybrid_search_engine.py:495 — app.services.hybrid_search_engine.HybridSearchEngine._get_recency_boost (score 0.28)
   Evidence: Score 0.28, Get boost based on content recency
5) app/services/knowledge_search_service.py:377 — app.services.knowledge_search_service.KnowledgeSearchService._combine_and_deduplicate_results (score 0.28)
   Evidence: Score 0.28, Combine results from BM25 and vector search, removing duplicates.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->