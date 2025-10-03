# RAG STEP 75 — Response has tool_calls? (RAG.response.response.has.tool.calls)

**Type:** process  
**Category:** response  
**Node ID:** `ToolCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolCheck` (Response has tool_calls?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/response.py:431` - `step_75__tool_check()`
- **Role:** Node
- **Status:** missing
- **Behavior notes:** Async orchestrator checking if response contains tool calls. Decision point routing to tool execution or simple message response.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing response processing infrastructure

## TDD Task List
- [x] Unit tests (response processing, workflow execution, message handling)
- [x] Integration tests (response workflow flow and message routing)
- [x] Implementation changes (async orchestrator with response processing, workflow execution, message handling)
- [x] Observability: add structured log line
  `RAG STEP 75 (...): ... | attrs={response_type, processing_time, message_count}`
- [x] Feature flag / config if needed (response workflow configuration and timeout settings)
- [x] Rollout plan (implemented with response processing reliability and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.34

Top candidates:
1) app/orchestrators/response.py:431 — app.orchestrators.response.step_75__tool_check (score 0.34)
   Evidence: Score 0.34, RAG STEP 75 — Response has tool_calls?
ID: RAG.response.response.has.tool.calls
...
2) app/core/langgraph/nodes/step_075__tool_check.py:9 — app.core.langgraph.nodes.step_075__tool_check.node_step_75 (score 0.27)
   Evidence: Score 0.27, Node wrapper for Step 75: Check if tools are needed.
3) app/core/langgraph/graph.py:1012 — app.core.langgraph.graph.LangGraphAgent._route_from_tool_check (score 0.27)
   Evidence: Score 0.27, Route from ToolCheck node.
4) app/api/v1/api.py:64 — app.api.v1.api.health_check (score 0.26)
   Evidence: Score 0.26, Health check endpoint.

Returns:
    dict: Health status information.
5) app/main.py:157 — app.main.health_check (score 0.26)
   Evidence: Score 0.26, Health check endpoint with environment-specific information.

Returns:
    Dict[...

Notes:
- Strong implementation match found
- Low confidence in symbol matching
- Wired via graph registry ✅
- Incoming: [74], Outgoing: [79]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->