# RAG STEP 108 — write_sse Format chunks (RAG.streaming.write.sse.format.chunks)

**Type:** process
**Category:** streaming
**Node ID:** `WriteSSE`

## Intent (Blueprint)
Formats streaming chunks into Server-Sent Events (SSE) format using the write_sse function. Transforms protected async generator streams into proper SSE format for browser consumption. Essential step that bridges stream protection to streaming response delivery, enabling proper SSE formatting with logging and error handling. Routes from SinglePass (Step 107) to StreamingResponse (Step 109). This step is derived from the Mermaid node: `WriteSSE` (write_sse Format chunks).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_108__write_sse.py` - `node_step_108`, `app/orchestrators/streaming.py:287` - `step_108__write_sse()`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Async orchestrator that formats streaming chunks into SSE format using the existing write_sse function. Creates SSE-formatted generator, configures formatting options, and validates requirements. Routes to StreamingResponse (Step 109) with properly formatted SSE stream ready for delivery.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing write_sse formatting logic

## TDD Task List
- [x] Unit tests (SSE formatting, configuration settings, complex chunks, context preservation, metadata addition, validation requirements, SSE options, stream errors, formatting parameters, logging)
- [x] Parity tests (SSE formatting behavior verification)
- [x] Integration tests (SinglePass→WriteSSE→StreamingResponse flow, error handling)
- [x] Implementation changes (async SSE formatting orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 108 (RAG.streaming.write.sse.format.chunks): write_sse Format chunks | attrs={step, request_id, chunks_formatted, format_configured, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing write_sse infrastructure)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_108
- Incoming edges: [107]
- Outgoing edges: [109]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->