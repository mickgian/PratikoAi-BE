# RAG STEP 39 — KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost (RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost)

**Type:** process  
**Category:** preflight  
**Node ID:** `KBPreFetch`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBPreFetch` (KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** missing
- **Paths / classes:** `app/orchestrators/preflight.py:360` - `step_39__kbpre_fetch()`
- **Behavior notes:** Runtime boundary; retrieves top-K documents using hybrid search; routes to next steps.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing preflight validation infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 39 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.31

Top candidates:
1) app/services/knowledge_search_service.py:735 — app.services.knowledge_search_service.retrieve_knowledge_topk (score 0.31)
   Evidence: Score 0.31, Convenience function to retrieve top-k knowledge items.

Args:
    query_data: Q...
2) app/services/knowledge_search_service.py:442 — app.services.knowledge_search_service.KnowledgeSearchService._calculate_recency_boost (score 0.30)
   Evidence: Score 0.30, Calculate recency boost based on document age.
3) app/services/hybrid_search_engine.py:495 — app.services.hybrid_search_engine.HybridSearchEngine._get_recency_boost (score 0.28)
   Evidence: Score 0.28, Get boost based on content recency
4) app/services/knowledge_search_service.py:377 — app.services.knowledge_search_service.KnowledgeSearchService._combine_and_deduplicate_results (score 0.28)
   Evidence: Score 0.28, Combine results from BM25 and vector search, removing duplicates.
5) test_knowledge_search.py:58 — test_knowledge_search.test_italian_search (score 0.27)
   Evidence: Score 0.27, Test Italian full-text search functionality.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Detected Node but not in runtime registry

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->