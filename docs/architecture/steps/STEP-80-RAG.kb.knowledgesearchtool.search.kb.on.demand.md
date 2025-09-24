# RAG STEP 80 — KnowledgeSearchTool.search KB on demand (RAG.kb.knowledgesearchtool.search.kb.on.demand)

**Type:** process  
**Category:** kb  
**Node ID:** `KBQueryTool`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBQueryTool` (KnowledgeSearchTool.search KB on demand).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/kb.py:step_80__kbquery_tool`, `app/core/langgraph/tools/knowledge_search_tool.py:KnowledgeSearchTool`
- **Status:** ✅ Implemented
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
Status: ✅  |  Confidence: 1.00

Top candidates:
1) app/orchestrators/kb.py:32 — app.orchestrators.kb.step_80__kbquery_tool (score 1.00)
   Evidence: Score 1.00, RAG STEP 80 — KnowledgeSearchTool.search KB on demand
ID: RAG.kb.knowledgesearchtool.search.kb.on.demand
Type: process
2) app/core/langgraph/tools/knowledge_search_tool.py:43 — app.core.langgraph.tools.knowledge_search_tool.KnowledgeSearchTool (score 0.95)
   Evidence: Score 0.95, LangGraph tool for searching the knowledge base on demand.
3) app/services/knowledge_search_service.py:735 — app.services.knowledge_search_service.retrieve_knowledge_topk (score 0.85)
   Evidence: Score 0.85, Convenience function to retrieve top-k knowledge items.

Notes:
- ✅ Implementation complete and wired correctly
- ✅ Async orchestrator wrapping KnowledgeSearchService
- ✅ KnowledgeSearchTool created for LangGraph
- ✅ 11/11 tests passing
- ✅ Routes to Step 99 (ToolResults) per Mermaid

Completed TDD actions:
- ✅ Created thin async orchestrator in app/orchestrators/kb.py
- ✅ Added KnowledgeSearchTool to LangGraph tools
- ✅ Implemented 11 comprehensive tests (unit + parity + integration)
- ✅ Added structured observability logging
<!-- AUTO-AUDIT:END -->