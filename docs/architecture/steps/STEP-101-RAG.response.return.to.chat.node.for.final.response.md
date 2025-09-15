# RAG STEP 101 — Return to chat node for final response (RAG.response.return.to.chat.node.for.final.response)

**Type:** process  
**Category:** response  
**Node ID:** `FinalResponse`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FinalResponse` (Return to chat node for final response).

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
  `RAG STEP 101 (RAG.response.return.to.chat.node.for.final.response): Return to chat node for final response | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.31)
   Evidence: Score 0.31, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
2) app/schemas/chat.py:19 — app.schemas.chat.Message (score 0.27)
   Evidence: Score 0.27, Message model for chat endpoint.

Attributes:
    role: The role of the message ...
3) app/schemas/chat.py:57 — app.schemas.chat.QueryClassificationMetadata (score 0.27)
   Evidence: Score 0.27, Metadata about query classification for debugging and monitoring.
4) app/schemas/chat.py:70 — app.schemas.chat.ResponseMetadata (score 0.27)
   Evidence: Score 0.27, Response metadata for debugging and monitoring.
5) app/schemas/chat.py:81 — app.schemas.chat.ChatRequest (score 0.27)
   Evidence: Score 0.27, Request model for chat endpoint.

Attributes:
    messages: List of messages in ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->