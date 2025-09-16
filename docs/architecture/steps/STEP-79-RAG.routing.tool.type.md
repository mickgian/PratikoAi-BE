# RAG STEP 79 — Tool type? (RAG.routing.tool.type)

**Type:** decision  
**Category:** routing  
**Node ID:** `ToolType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolType` (Tool type?).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/graph.py:LangGraphAgent._detect_tool_type`, `app/core/langgraph/graph.py:LangGraphAgent._log_tool_type_decision`, `app/core/langgraph/graph.py:LangGraphAgent._get_routing_decision`
- **Status:** ✅ Implemented
- **Behavior notes:** Tool type detection is fully implemented with structured logging. Detects Knowledge, CCNL, Document, FAQ, and Unknown tool types. Integrated into _tool_call method with proper timing and logging.

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [x] Unit tests (tool type detection, routing decisions, error handling)
- [x] Integration tests (end-to-end tool routing flow)
- [x] Implementation changes (tool type detection methods added to LangGraphAgent)
- [x] Observability: add structured log line  
  `RAG STEP 79 (RAG.routing.tool.type): Tool type? | attrs={tool_name, tool_type, decision}`
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
1) app/ragsteps/routing/step_79_rag_routing_tool_type.py:64 — app.ragsteps.routing.step_79_rag_routing_tool_type.step_79_rag_routing_tool_type (score 0.27)
   Evidence: Score 0.27, Canonical symbol for auditor: STEP 79 — Tool type? (RAG.routing.tool.type)

Dele...
2) app/core/langgraph/tools/ccnl_tool.py:83 — app.core.langgraph.tools.ccnl_tool.CCNLTool.__init__ (score 0.27)
   Evidence: Score 0.27, method: __init__
3) app/core/langgraph/tools/ccnl_tool.py:101 — app.core.langgraph.tools.ccnl_tool.CCNLTool._run (score 0.27)
   Evidence: Score 0.27, Execute CCNL query (synchronous version).
4) app/core/langgraph/tools/document_ingest_tool.py:80 — app.core.langgraph.tools.document_ingest_tool.DocumentIngestTool.__init__ (score 0.27)
   Evidence: Score 0.27, Initialize the document ingest tool.
5) app/core/langgraph/tools/document_ingest_tool.py:374 — app.core.langgraph.tools.document_ingest_tool.DocumentIngestTool._run (score 0.27)
   Evidence: Score 0.27, Synchronous wrapper (not recommended, use async version).

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for ToolType
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->