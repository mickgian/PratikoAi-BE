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
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/schemas/chat.py:95 — app.schemas.chat.ChatResponse (score 0.29)
   Evidence: Score 0.29, Response model for chat endpoint.

Attributes:
    messages: List of messages in...
2) app/schemas/chat.py:70 — app.schemas.chat.ResponseMetadata (score 0.28)
   Evidence: Score 0.28, Response metadata for debugging and monitoring.
3) app/schemas/chat.py:107 — app.schemas.chat.StreamResponse (score 0.28)
   Evidence: Score 0.28, Response model for streaming chat endpoint.

Attributes:
    content: The conten...
4) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.26)
   Evidence: Score 0.26, Convert internal SearchResponse to API model.
5) app/core/decorators/cache.py:19 — app.core.decorators.cache.cache_llm_response (score 0.26)
   Evidence: Score 0.26, Decorator to cache LLM responses based on messages and model.

Args:
    ttl: Ti...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ReturnComplete
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->