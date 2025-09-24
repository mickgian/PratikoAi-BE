# RAG STEP 105 — ChatbotController.chat_stream Setup SSE (RAG.streaming.chatbotcontroller.chat.stream.setup.sse)

**Type:** process  
**Category:** streaming  
**Node ID:** `StreamSetup`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StreamSetup` (ChatbotController.chat_stream Setup SSE).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 105 (RAG.streaming.chatbotcontroller.chat.stream.setup.sse): ChatbotController.chat_stream Setup SSE | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.34

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
4) app/orchestrators/streaming.py:32 — app.orchestrators.streaming.step_105__stream_setup (score 0.28)
   Evidence: Score 0.28, RAG STEP 105 — ChatbotController.chat_stream Setup SSE
ID: RAG.streaming.chatbot...
5) app/schemas/chat.py:107 — app.schemas.chat.StreamResponse (score 0.26)
   Evidence: Score 0.26, Response model for streaming chat endpoint.

Attributes:
    content: The conten...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->