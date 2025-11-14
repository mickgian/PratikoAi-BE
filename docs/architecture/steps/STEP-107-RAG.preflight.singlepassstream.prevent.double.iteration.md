# RAG STEP 107 — SinglePassStream Prevent double iteration (RAG.preflight.singlepassstream.prevent.double.iteration)

**Type:** process
**Category:** preflight
**Node ID:** `SinglePass`

## Intent (Blueprint)
Wraps async generators with SinglePassStream to prevent double iteration and streaming duplication. Ensures streaming safety by protecting against accidental re-iteration of generators that could cause duplicate content delivery. Essential step that bridges async generator creation to SSE formatting, enabling secure stream consumption. Routes from AsyncGen (Step 106) to WriteSSE (Step 108). This step is derived from the Mermaid node: `SinglePass` (SinglePassStream Prevent double iteration).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_107__single_pass.py` - `node_step_107`, `app/orchestrators/preflight.py:744` - `step_107__single_pass()`
- **Role:** Internal
- **Status:** 🔌
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_107
- Incoming edges: [106]
- Outgoing edges: [108]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->