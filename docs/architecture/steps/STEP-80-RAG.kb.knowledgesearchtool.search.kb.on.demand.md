# RAG STEP 80 — KnowledgeSearchTool.search KB on demand (RAG.kb.knowledgesearchtool.search.kb.on.demand)

**Type:** process  
**Category:** kb  
**Node ID:** `KBQueryTool`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBQueryTool` (KnowledgeSearchTool.search KB on demand).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/kb.py:150` - `step_80__kbquery_tool()`
- **Role:** Node
- **Status:** missing
- **Behavior notes:** Thin async orchestrator that executes on-demand knowledge base search when the LLM calls the KnowledgeSearchTool. Uses KnowledgeSearchService for hybrid BM25 + vector + recency search. Routes to Step 99 (ToolResults).

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing KnowledgeSearchService infrastructure

## TDD Task List
- [x] Unit tests (KB search execution, query handling, hybrid results, empty results, metadata, routing, context preservation)
- [x] Integration tests (Step 79→80→99 flow, Step 99 preparation)
- [x] Implementation changes (thin async orchestrator wrapping KnowledgeSearchService, KnowledgeSearchTool for LangGraph)
- [x] Observability: add structured log line
  `RAG STEP 80 (RAG.kb.knowledgesearchtool.search.kb.on.demand): KnowledgeSearchTool.search KB on demand | attrs={...}`
- [x] Feature flag / config if needed (uses existing KnowledgeSearchService configuration)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.47

Top candidates:
1) app/services/knowledge_search_service.py:735 — app.services.knowledge_search_service.retrieve_knowledge_topk (score 0.47)
   Evidence: Score 0.47, Convenience function to retrieve top-k knowledge items.

Args:
    query_data: Q...
2) app/core/langgraph/tools/knowledge_search_tool.py:69 — app.core.langgraph.tools.knowledge_search_tool.KnowledgeSearchTool._run (score 0.45)
   Evidence: Score 0.45, Execute knowledge search (synchronous version).
3) app/services/knowledge_search_service.py:1 — app.services.knowledge_search_service (score 0.45)
   Evidence: Score 0.45, Knowledge Search Service - RAG STEP 39 Implementation.

Implements RAG STEP 39 —...
4) app/services/knowledge_search_service.py:97 — app.services.knowledge_search_service.KnowledgeSearchService (score 0.45)
   Evidence: Score 0.45, Service for hybrid knowledge search with BM25, vector search and recency boost.
5) app/services/knowledge_search_service.py:32 — app.services.knowledge_search_service.SearchMode (score 0.44)
   Evidence: Score 0.44, Search mode for knowledge retrieval.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->