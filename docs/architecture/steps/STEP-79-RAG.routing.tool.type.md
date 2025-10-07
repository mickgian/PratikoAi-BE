# RAG STEP 79 — Tool type? (RAG.routing.tool.type)

**Type:** decision  
**Category:** routing  
**Node ID:** `ToolType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolType` (Tool type?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/routing.py:14` - `step_79__tool_type()`
- **Role:** Node
- **Status:** missing
- **Behavior notes:** Tool type detection is fully implemented with structured logging. Detects Knowledge, CCNL, Document, FAQ, and Unknown tool types. Integrated into _tool_call method with proper timing and logging.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - graceful degradation with existing error handling

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
Role: Node  |  Status: ❌ (Missing)  |  Confidence: 0.29

Top candidates:
1) app/core/langgraph/graph.py:980 — app.core.langgraph.graph.LangGraphAgent._route_tool_type (score 0.29)
   Evidence: Score 0.29, Route from ToolType node based on tool type.
2) app/core/langgraph/graph.py:1060 — app.core.langgraph.graph.LangGraphAgent._route_from_tool_type (score 0.28)
   Evidence: Score 0.28, Route from ToolType node based on tool type.
3) app/orchestrators/platform.py:2024 — app.orchestrators.platform.step_78__execute_tools (score 0.27)
   Evidence: Score 0.27, RAG STEP 78 — LangGraphAgent._tool_call Execute tools
ID: RAG.platform.langgraph...
4) app/orchestrators/routing.py:14 — app.orchestrators.routing.step_79__tool_type (score 0.27)
   Evidence: Score 0.27, RAG STEP 79 — Tool type?

ID: RAG.routing.tool.type
Type: decision | Category: r...
5) app/orchestrators/platform.py:2369 — app.orchestrators.platform._format_content_by_tool_type (score 0.27)
   Evidence: Score 0.27, Format tool result content based on tool type.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for ToolType
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->