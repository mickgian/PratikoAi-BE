# RAG STEP 108 — write_sse Format chunks (RAG.streaming.write.sse.format.chunks)

**Type:** process
**Category:** streaming
**Node ID:** `WriteSSE`

## Intent (Blueprint)
Formats streaming chunks into Server-Sent Events (SSE) format using the write_sse function. Transforms protected async generator streams into proper SSE format for browser consumption. Essential step that bridges stream protection to streaming response delivery, enabling proper SSE formatting with logging and error handling. Routes from SinglePass (Step 107) to StreamingResponse (Step 109). This step is derived from the Mermaid node: `WriteSSE` (write_sse Format chunks).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/streaming.py:287` - `step_108__write_sse()`
- **Status:** ✅ Implemented
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/core/sse_write.py:15 — app.core.sse_write.write_sse (score 0.32)
   Evidence: Score 0.32, Log an SSE frame that will be written to the response.

Args:
    response: The ...
2) app/orchestrators/streaming.py:287 — app.orchestrators.streaming.step_108__write_sse (score 0.29)
   Evidence: Score 0.29, RAG STEP 108 — write_sse Format chunks.

Thin async orchestrator that formats st...
3) app/orchestrators/streaming.py:387 — app.orchestrators.streaming._prepare_sse_format_configuration (score 0.29)
   Evidence: Score 0.29, Prepare configuration for SSE formatting.
4) app/orchestrators/streaming.py:446 — app.orchestrators.streaming._validate_sse_format_requirements (score 0.29)
   Evidence: Score 0.29, Validate SSE formatting requirements and return warnings.
5) evals/helpers.py:21 — evals.helpers.format_messages (score 0.27)
   Evidence: Score 0.27, Format a list of messages for evaluation.

Args:
    messages: List of message d...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->