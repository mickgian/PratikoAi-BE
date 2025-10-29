# RAG STEP 104 — Streaming requested? (RAG.streaming.streaming.requested)

**Type:** decision  
**Category:** streaming  
**Node ID:** `StreamCheck`

## Intent (Blueprint)
Determines if the client requested streaming response format by checking request parameters and HTTP headers. Routes to StreamSetup (Step 105) for streaming responses or ReturnComplete (Step 112) for regular JSON responses. Critical decision point that enables real-time response streaming based on client preferences. This step is derived from the Mermaid node: `StreamCheck` (Streaming requested?).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_104__stream_check.py` - `node_step_104`, `app/orchestrators/streaming.py:15` - `step_104__stream_check()`
- **Role:** Node
- **Status:** ✅
- **Behavior notes:** Async decision orchestrator that checks stream parameter, HTTP Accept headers, and client preferences. Routes to StreamSetup for streaming or ReturnComplete for JSON responses. Includes streaming configuration setup and comprehensive value parsing for various stream parameter formats.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing streaming detection logic

## TDD Task List
- [x] Unit tests (streaming detection, non-streaming, missing parameters, string values, HTTP headers, context preservation, decision metadata, streaming configuration, edge cases, logging)
- [x] Parity tests (streaming decision behavior verification)
- [x] Integration tests (LogComplete→StreamCheck→StreamSetup/ReturnComplete flow)
- [x] Implementation changes (async streaming decision orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 104 (RAG.streaming.streaming.requested): Streaming requested? | attrs={step, request_id, streaming_requested, decision, decision_source, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing detection logic)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_104
- Incoming edges: none
- Outgoing edges: [105, 111]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->