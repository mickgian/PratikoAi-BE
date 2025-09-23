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
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/orchestrators/streaming.py:32 — app.orchestrators.streaming.step_105__stream_setup (score 0.28)
   Evidence: Score 0.28, RAG STEP 105 — ChatbotController.chat_stream Setup SSE
ID: RAG.streaming.chatbot...
2) app/schemas/chat.py:107 — app.schemas.chat.StreamResponse (score 0.26)
   Evidence: Score 0.26, Response model for streaming chat endpoint.

Attributes:
    content: The conten...
3) app/core/logging.py:174 — app.core.logging.setup_logging (score 0.26)
   Evidence: Score 0.26, Configure structlog with different formatters based on environment.

In developm...
4) app/core/metrics.py:39 — app.core.metrics.setup_metrics (score 0.26)
   Evidence: Score 0.26, Set up Prometheus metrics middleware and endpoints.

Args:
    app: FastAPI appl...
5) app/core/sse_write.py:15 — app.core.sse_write.write_sse (score 0.26)
   Evidence: Score 0.26, Log an SSE frame that will be written to the response.

Args:
    response: The ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for StreamSetup
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->