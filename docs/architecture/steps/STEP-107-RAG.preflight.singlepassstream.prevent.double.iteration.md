# RAG STEP 107 — SinglePassStream Prevent double iteration (RAG.preflight.singlepassstream.prevent.double.iteration)

**Type:** process
**Category:** preflight
**Node ID:** `SinglePass`

## Intent (Blueprint)
Wraps async generators with SinglePassStream to prevent double iteration and streaming duplication. Ensures streaming safety by protecting against accidental re-iteration of generators that could cause duplicate content delivery. Essential step that bridges async generator creation to SSE formatting, enabling secure stream consumption. Routes from AsyncGen (Step 106) to WriteSSE (Step 108). This step is derived from the Mermaid node: `SinglePass` (SinglePassStream Prevent double iteration).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/preflight.py:744` - `step_107__single_pass()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that wraps async generators with SinglePassStream protection to prevent double iteration. Configures stream protection settings, validates requirements, and prepares for SSE formatting. Routes to WriteSSE (Step 108) with protected stream ready for consumption.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing SinglePassStream protection logic

## TDD Task List
- [x] Unit tests (stream wrapping, protection configuration, complex generators, context preservation, metadata addition, validation requirements, protection settings, generator errors, streaming options, logging)
- [x] Parity tests (stream protection behavior verification)
- [x] Integration tests (AsyncGen→SinglePass→WriteSSE flow, error handling)
- [x] Implementation changes (async stream protection orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 107 (RAG.preflight.singlepassstream.prevent.double.iteration): SinglePassStream Prevent double iteration | attrs={step, request_id, stream_protected, protection_configured, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing SinglePassStream infrastructure)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/core/streaming_guard.py:19 — app.core.streaming_guard.SinglePassStream.__init__ (score 0.31)
   Evidence: Score 0.31, method: __init__
2) app/core/streaming_guard.py:23 — app.core.streaming_guard.SinglePassStream.__aiter__ (score 0.31)
   Evidence: Score 0.31, method: __aiter__
3) app/core/streaming_guard.py:13 — app.core.streaming_guard.SinglePassStream (score 0.28)
   Evidence: Score 0.28, Wraps an async generator to ensure it's only iterated once.
Raises RuntimeError ...
4) app/orchestrators/preflight.py:744 — app.orchestrators.preflight.step_107__single_pass (score 0.28)
   Evidence: Score 0.28, RAG STEP 107 — SinglePassStream Prevent double iteration

Thin async orchestrato...
5) app/orchestrators/preflight.py:804 — app.orchestrators.preflight._wrap_with_single_pass_protection (score 0.27)
   Evidence: Score 0.27, Wrap async generator with SinglePassStream to prevent double iteration.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->