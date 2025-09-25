# RAG STEP 106 — Create async generator (RAG.platform.create.async.generator)

**Type:** process
**Category:** platform
**Node ID:** `AsyncGen`

## Intent (Blueprint)
Creates an async generator for streaming response delivery. Configures streaming parameters, session data, and provider settings to enable real-time response streaming. Essential step that bridges streaming setup to actual response generation, enabling browser-compatible async iteration. Routes from StreamSetup (Step 105) to SinglePassStream (Step 107). This step is derived from the Mermaid node: `AsyncGen` (Create async generator).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:step_106__async_gen`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that creates async generator with proper streaming configuration, session data, and provider settings. Handles generator configuration, validation, and metadata preparation. Routes to SinglePassStream (Step 107) with complete async generator ready for consumption.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing async generator creation logic

## TDD Task List
- [x] Unit tests (async generator creation, configuration settings, complex messages, context preservation, metadata addition, streaming parameters, custom options, validation requirements, provider-specific config, logging)
- [x] Parity tests (generator creation behavior verification)
- [x] Integration tests (StreamSetup→AsyncGen→SinglePassStream flow, error handling)
- [x] Implementation changes (async generator creation orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 106 (RAG.platform.create.async.generator): Create async generator | attrs={step, request_id, generator_created, generator_configured, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing async generator infrastructure)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/platform.py:2781 — app.orchestrators.platform._create_streaming_generator (score 0.30)
   Evidence: Score 0.30, Create async generator for streaming response delivery.
2) app/orchestrators/platform.py:2721 — app.orchestrators.platform.step_106__async_gen (score 0.29)
   Evidence: Score 0.29, RAG STEP 106 — Create async generator

Thin async orchestrator that creates an a...
3) app/orchestrators/streaming.py:346 — app.orchestrators.streaming._create_sse_formatted_generator (score 0.29)
   Evidence: Score 0.29, Create SSE-formatted generator using write_sse function.
4) app/api/v1/faq.py:385 — app.api.v1.faq.create_faq (score 0.27)
   Evidence: Score 0.27, Create a new FAQ entry.

Requires admin privileges.
5) app/api/v1/auth.py:265 — app.api.v1.auth.create_session (score 0.26)
   Evidence: Score 0.26, Create a new chat session for the authenticated user.

Args:
    user: The authe...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for AsyncGen
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->