# RAG STEP 105 — ChatbotController.chat_stream Setup SSE (RAG.streaming.chatbotcontroller.chat.stream.setup.sse)

**Type:** process  
**Category:** streaming  
**Node ID:** `StreamSetup`

## Intent (Blueprint)
Sets up Server-Sent Events (SSE) streaming infrastructure for real-time response delivery. Configures SSE headers, streaming context, and prepares for async generator creation. Essential step that bridges streaming decision to actual response generation, enabling browser-compatible event streaming. Routes to AsyncGen (Step 106) for generator creation. This step is derived from the Mermaid node: `StreamSetup` (ChatbotController.chat_stream Setup SSE).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_105__stream_setup.py` - `node_step_105`, `app/orchestrators/streaming.py:149` - `step_105__stream_setup()`
- **Role:** Node
- **Status:** ✅ Implemented
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.34

Top candidates:
1) app/api/v1/chatbot.py:111 — app.api.v1.chatbot.chat_stream (score 0.34)
   Evidence: Score 0.34, Process a chat request using LangGraph with streaming response.

Args:
    reque...
2) app/api/v1/chatbot.py:42 — app.api.v1.chatbot.chat (score 0.30)
   Evidence: Score 0.30, Process a chat request using LangGraph.

Args:
    request: The FastAPI request ...
3) app/api/v1/chatbot.py:247 — app.api.v1.chatbot.clear_chat_history (score 0.28)
   Evidence: Score 0.28, Clear all messages for a session.

Args:
    request: The FastAPI request object...
4) app/orchestrators/streaming.py:149 — app.orchestrators.streaming.step_105__stream_setup (score 0.28)
   Evidence: Score 0.28, RAG STEP 105 — ChatbotController.chat_stream Setup SSE.

Thin async orchestrator...
5) app/core/langgraph/nodes/step_105__stream_setup.py:9 — app.core.langgraph.nodes.step_105__stream_setup.node_step_105 (score 0.27)
   Evidence: Score 0.27, Node wrapper for Step 105: Setup SSE streaming infrastructure.

Notes:
- Strong implementation match found
- Low confidence in symbol matching
- Wired via graph registry ✅
- Incoming: [104], Outgoing: [106]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->