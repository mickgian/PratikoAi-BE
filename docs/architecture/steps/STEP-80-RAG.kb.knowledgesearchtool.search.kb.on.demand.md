# RAG STEP 80 — KnowledgeSearchTool.search KB on demand (RAG.kb.knowledgesearchtool.search.kb.on.demand)

**Type:** process  
**Category:** kb  
**Node ID:** `KBQueryTool`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBQueryTool` (KnowledgeSearchTool.search KB on demand).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/kb.py:150` - `step_80__kbquery_tool()`
- **Role:** Node
- **Status:** ✅
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_80
- Incoming edges: [79]
- Outgoing edges: [99]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->