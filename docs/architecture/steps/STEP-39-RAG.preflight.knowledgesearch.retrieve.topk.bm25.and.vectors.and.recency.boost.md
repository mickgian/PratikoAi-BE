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
Status: 🔌  |  Confidence: 0.30

Top candidates:
1) app/services/knowledge_search_service.py:442 — app.services.knowledge_search_service.KnowledgeSearchService._calculate_recency_boost (score 0.30)
   Evidence: Score 0.30, Calculate recency boost based on document age.
2) app/services/hybrid_search_engine.py:495 — app.services.hybrid_search_engine.HybridSearchEngine._get_recency_boost (score 0.28)
   Evidence: Score 0.28, Get boost based on content recency
3) app/services/knowledge_search_service.py:377 — app.services.knowledge_search_service.KnowledgeSearchService._combine_and_deduplicate_results (score 0.28)
   Evidence: Score 0.28, Combine results from BM25 and vector search, removing duplicates.
4) app/services/knowledge_search_service.py:100 — app.services.knowledge_search_service.KnowledgeSearchService.__init__ (score 0.27)
   Evidence: Score 0.27, Initialize knowledge search service.
5) app/services/knowledge_search_service.py:80 — app.services.knowledge_search_service.SearchResult.to_dict (score 0.26)
   Evidence: Score 0.26, Convert to dictionary for structured logging.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->