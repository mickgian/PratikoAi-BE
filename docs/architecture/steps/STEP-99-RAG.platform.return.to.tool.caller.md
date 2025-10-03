# RAG STEP 99 — Return to tool caller (RAG.platform.return.to.tool.caller)

**Type:** process  
**Category:** platform  
**Node ID:** `ToolResults`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolResults` (Return to tool caller).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/platform.py:2526` - `step_99__tool_results()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator returning tool execution results to the LLM for further processing. Formats tool responses and integrates them back into the conversation flow for multi-step interactions.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 99 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.32

Top candidates:
1) app/orchestrators/platform.py:2248 — app.orchestrators.platform._format_tool_results_for_caller (score 0.32)
   Evidence: Score 0.32, Format tool results from various tool types into ToolMessage format for LangGrap...
2) app/orchestrators/facts.py:675 — app.orchestrators.facts.step_98__to_tool_results (score 0.30)
   Evidence: Score 0.30, RAG STEP 98 — Convert to ToolMessage facts and spans
ID: RAG.facts.convert.to.to...
3) app/orchestrators/platform.py:2526 — app.orchestrators.platform.step_99__tool_results (score 0.30)
   Evidence: Score 0.30, RAG STEP 99 — Return to tool caller.

ID: RAG.platform.return.to.tool.caller
Typ...
4) app/orchestrators/platform.py:2491 — app.orchestrators.platform._handle_tool_results_error (score 0.29)
   Evidence: Score 0.29, Handle errors in tool results processing with graceful fallback.
5) app/core/langgraph/nodes/step_099__tool_results.py:9 — app.core.langgraph.nodes.step_099__tool_results.node_step_99 (score 0.28)
   Evidence: Score 0.28, Node wrapper for Step 99: Process and aggregate tool results.

Notes:
- Strong implementation match found
- Low confidence in symbol matching
- Wired via graph registry ✅
- Incoming: [80, 81, 82, 83], Outgoing: []

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->