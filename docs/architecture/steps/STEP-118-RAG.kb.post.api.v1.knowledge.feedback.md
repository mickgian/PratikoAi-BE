# RAG STEP 118 — POST /api/v1/knowledge/feedback (RAG.kb.post.api.v1.knowledge.feedback)

**Type:** process  
**Category:** kb  
**Node ID:** `KnowledgeFeedback`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KnowledgeFeedback` (POST /api/v1/knowledge/feedback).

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
  `RAG STEP 118 (RAG.kb.post.api.v1.knowledge.feedback): POST /api/v1/knowledge/feedback | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.47

Top candidates:
1) app/services/knowledge_search_service.py:735 — app.services.knowledge_search_service.retrieve_knowledge_topk (score 0.47)
   Evidence: Score 0.47, Convenience function to retrieve top-k knowledge items.

Args:
    query_data: Q...
2) app/api/v1/search.py:772 — app.api.v1.search.reindex_knowledge_fts (score 0.46)
   Evidence: Score 0.46, Manually reindex knowledge base search vectors.

Admin endpoint for maintenance ...
3) app/api/v1/search.py:627 — app.api.v1.search.submit_knowledge_feedback (score 0.45)
   Evidence: Score 0.45, Submit feedback on knowledge search results.

Helps improve search relevance and...
4) app/services/knowledge_search_service.py:1 — app.services.knowledge_search_service (score 0.45)
   Evidence: Score 0.45, Knowledge Search Service - RAG STEP 39 Implementation.

Implements RAG STEP 39 —...
5) app/services/knowledge_search_service.py:97 — app.services.knowledge_search_service.KnowledgeSearchService (score 0.45)
   Evidence: Score 0.45, Service for hybrid knowledge search with BM25, vector search and recency boost.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->