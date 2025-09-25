# RAG STEP 30 — Return ChatResponse (RAG.response.return.chatresponse)

**Type:** process  
**Category:** response  
**Node ID:** `ReturnComplete`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReturnComplete` (Return ChatResponse).

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
  `RAG STEP 30 (RAG.response.return.chatresponse): Return ChatResponse | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.35

Top candidates:
1) app/orchestrators/response.py:163 — app.orchestrators.response.step_30__return_complete (score 0.35)
   Evidence: Score 0.35, RAG STEP 30 — Return ChatResponse
ID: RAG.response.return.chatresponse
Type: pro...
2) app/schemas/chat.py:95 — app.schemas.chat.ChatResponse (score 0.29)
   Evidence: Score 0.29, Response model for chat endpoint.

Attributes:
    messages: List of messages in...
3) app/schemas/chat.py:70 — app.schemas.chat.ResponseMetadata (score 0.28)
   Evidence: Score 0.28, Response metadata for debugging and monitoring.
4) app/schemas/chat.py:107 — app.schemas.chat.StreamResponse (score 0.28)
   Evidence: Score 0.28, Response model for streaming chat endpoint.

Attributes:
    content: The conten...
5) app/api/v1/chatbot.py:42 — app.api.v1.chatbot.chat (score 0.27)
   Evidence: Score 0.27, Process a chat request using LangGraph.

Args:
    request: The FastAPI request ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->