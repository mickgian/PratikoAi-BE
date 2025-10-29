# RAG STEP 105 — ChatbotController.chat_stream Setup SSE (RAG.streaming.chatbotcontroller.chat.stream.setup.sse)

**Type:** process  
**Category:** streaming  
**Node ID:** `StreamSetup`

## Intent (Blueprint)
Sets up Server-Sent Events (SSE) streaming infrastructure for real-time response delivery. Configures SSE headers, streaming context, and prepares for async generator creation. Essential step that bridges streaming decision to actual response generation, enabling browser-compatible event streaming. Routes to AsyncGen (Step 106) for generator creation. This step is derived from the Mermaid node: `StreamSetup` (ChatbotController.chat_stream Setup SSE).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_105__stream_setup.py` - `node_step_105`, `app/orchestrators/streaming.py:149` - `step_105__stream_setup()`
- **Role:** Node
- **Status:** ✅
- **Behavior notes:** Async orchestrator that configures SSE headers (Content-Type, Cache-Control, CORS), prepares streaming context with session data, and validates streaming requirements. Handles custom headers, compression settings, and heartbeat configuration. Routes to AsyncGen (Step 106) with complete streaming infrastructure ready.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing SSE streaming logic

## TDD Task List
- [x] Unit tests (SSE configuration, headers setup, stream context preparation, custom options, context preservation, metadata addition, CORS configuration, compression settings, requirements validation, heartbeat configuration, logging)
- [x] Parity tests (SSE setup behavior verification)
- [x] Integration tests (StreamCheck→StreamSetup→AsyncGen flow, error handling)
- [x] Implementation changes (async SSE streaming setup orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 105 (RAG.streaming.chatbotcontroller.chat.stream.setup.sse): ChatbotController.chat_stream Setup SSE | attrs={step, request_id, streaming_requested, streaming_setup, headers_configured, stream_context_prepared, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing SSE infrastructure)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_105
- Incoming edges: [104]
- Outgoing edges: [106]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->