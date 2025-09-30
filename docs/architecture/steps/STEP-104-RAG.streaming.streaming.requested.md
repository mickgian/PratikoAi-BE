# RAG STEP 104 — Streaming requested? (RAG.streaming.streaming.requested)

**Type:** decision  
**Category:** streaming  
**Node ID:** `StreamCheck`

## Intent (Blueprint)
Determines if the client requested streaming response format by checking request parameters and HTTP headers. Routes to StreamSetup (Step 105) for streaming responses or ReturnComplete (Step 112) for regular JSON responses. Critical decision point that enables real-time response streaming based on client preferences. This step is derived from the Mermaid node: `StreamCheck` (Streaming requested?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/streaming.py:15` - `step_104__stream_check()`
- **Role:** Node
- **Status:** missing
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.34

Top candidates:
1) app/orchestrators/streaming.py:15 — app.orchestrators.streaming.step_104__stream_check (score 0.34)
   Evidence: Score 0.34, RAG STEP 104 — Streaming requested?

Thin async orchestrator that determines if ...
2) app/orchestrators/streaming.py:115 — app.orchestrators.streaming._parse_stream_value (score 0.30)
   Evidence: Score 0.30, Parse various stream value formats to boolean.
3) app/orchestrators/streaming.py:239 — app.orchestrators.streaming._prepare_stream_context (score 0.30)
   Evidence: Score 0.30, Prepare streaming context for async generator creation.
4) app/orchestrators/streaming.py:149 — app.orchestrators.streaming.step_105__stream_setup (score 0.29)
   Evidence: Score 0.29, RAG STEP 105 — ChatbotController.chat_stream Setup SSE.

Thin async orchestrator...
5) app/orchestrators/streaming.py:575 — app.orchestrators.streaming.step_109__stream_response (score 0.29)
   Evidence: Score 0.29, RAG STEP 109 — StreamingResponse Send chunks.

Thin async orchestrator that crea...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->