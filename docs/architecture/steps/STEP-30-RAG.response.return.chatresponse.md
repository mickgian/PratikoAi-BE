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
1) app/orchestrators/response.py:162 — app.orchestrators.response.step_30__return_complete (score 0.35)
   Evidence: Score 0.35, RAG STEP 30 — Return ChatResponse.

ID: RAG.response.return.chatresponse
Type: p...
2) app/orchestrators/response.py:402 — app.orchestrators.response._handle_return_complete_error (score 0.34)
   Evidence: Score 0.34, Handle errors in ChatResponse formatting with graceful fallback.
3) app/orchestrators/response.py:235 — app.orchestrators.response._format_chat_response (score 0.31)
   Evidence: Score 0.31, Format context data into proper ChatResponse structure.

Handles various input f...
4) app/schemas/chat.py:95 — app.schemas.chat.ChatResponse (score 0.29)
   Evidence: Score 0.29, Response model for chat endpoint.

Attributes:
    messages: List of messages in...
5) app/schemas/chat.py:70 — app.schemas.chat.ResponseMetadata (score 0.28)
   Evidence: Score 0.28, Response metadata for debugging and monitoring.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->