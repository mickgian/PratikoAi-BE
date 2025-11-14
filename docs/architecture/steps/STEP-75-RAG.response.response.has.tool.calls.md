# RAG STEP 75 — Response has tool_calls? (RAG.response.response.has.tool.calls)

**Type:** process  
**Category:** response  
**Node ID:** `ToolCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolCheck` (Response has tool_calls?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/response.py:431` - `step_75__tool_check()`
- **Role:** Node
- **Status:** ✅
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_75
- Incoming edges: [74]
- Outgoing edges: [79]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->