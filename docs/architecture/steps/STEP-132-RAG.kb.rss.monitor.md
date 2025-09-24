# RAG STEP 132 — RSS Monitor (RAG.kb.rss.monitor)

**Type:** process  
**Category:** kb  
**Node ID:** `RSSMonitor`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RSSMonitor` (RSS Monitor).

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
  `RAG STEP 132 (RAG.kb.rss.monitor): RSS Monitor | attrs={...}`
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
2) app/services/knowledge_search_service.py:1 — app.services.knowledge_search_service (score 0.45)
   Evidence: Score 0.45, Knowledge Search Service - RAG STEP 39 Implementation.

Implements RAG STEP 39 —...
3) app/services/knowledge_search_service.py:97 — app.services.knowledge_search_service.KnowledgeSearchService (score 0.45)
   Evidence: Score 0.45, Service for hybrid knowledge search with BM25, vector search and recency boost.
4) app/services/knowledge_search_service.py:32 — app.services.knowledge_search_service.SearchMode (score 0.44)
   Evidence: Score 0.44, Search mode for knowledge retrieval.
5) app/services/vector_providers/pinecone_provider.py:21 — app.services.vector_providers.pinecone_provider.PineconeProvider (score 0.44)
   Evidence: Score 0.44, Pinecone vector search provider.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->