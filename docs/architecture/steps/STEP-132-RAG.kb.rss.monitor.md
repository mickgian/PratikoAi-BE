# RAG STEP 132 — RSS Monitor (RAG.kb.rss.monitor)

**Type:** process  
**Category:** kb  
**Node ID:** `RSSMonitor`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RSSMonitor` (RSS Monitor).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/kb.py:395` - `step_132__rssmonitor()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator monitoring RSS feeds for content updates. Periodically checks configured RSS sources for new content and triggers knowledge base updates when changes are detected.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing knowledge base infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 132 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

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