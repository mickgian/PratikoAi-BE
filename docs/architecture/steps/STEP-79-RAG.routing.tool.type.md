# RAG STEP 79 — Tool type? (RAG.routing.tool.type)

**Type:** decision  
**Category:** routing  
**Node ID:** `ToolType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolType` (Tool type?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/routing.py:14` - `step_79__tool_type()`
- **Role:** Node
- **Status:** ✅
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
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_79
- Incoming edges: [75]
- Outgoing edges: [80, 81, 82, 83]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->