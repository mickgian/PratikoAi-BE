# RAG STEP 106 — Create async generator (RAG.platform.create.async.generator)

**Type:** process
**Category:** platform
**Node ID:** `AsyncGen`

## Intent (Blueprint)
Creates an async generator for streaming response delivery. Configures streaming parameters, session data, and provider settings to enable real-time response streaming. Essential step that bridges streaming setup to actual response generation, enabling browser-compatible async iteration. Routes from StreamSetup (Step 105) to SinglePassStream (Step 107). This step is derived from the Mermaid node: `AsyncGen` (Create async generator).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_106__async_gen.py` - `node_step_106`, `app/orchestrators/platform.py:2721` - `step_106__async_gen()`
- **Role:** Internal
- **Status:** 🔌
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_106
- Incoming edges: [105]
- Outgoing edges: [107]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->