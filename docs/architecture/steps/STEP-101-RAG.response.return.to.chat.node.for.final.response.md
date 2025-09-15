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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/schemas/chat.py:95 — app.schemas.chat.ChatResponse (score 0.27)
   Evidence: Score 0.27, Response model for chat endpoint.

Attributes:
    messages: List of messages in...
2) app/schemas/chat.py:70 — app.schemas.chat.ResponseMetadata (score 0.26)
   Evidence: Score 0.26, Response metadata for debugging and monitoring.
3) app/schemas/chat.py:107 — app.schemas.chat.StreamResponse (score 0.26)
   Evidence: Score 0.26, Response model for streaming chat endpoint.

Attributes:
    content: The conten...
4) app/ragsteps/cache/step_59_rag_cache_langgraphagent_get_cached_llm_response_check_for_cached_response.py:40 — app.ragsteps.cache.step_59_rag_cache_langgraphagent_get_cached_llm_response_check_for_cached_response.run (score 0.26)
   Evidence: Score 0.26, Adapter for RAG STEP 59.

Expected behavior is defined in:
docs/architecture/ste...
5) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.25)
   Evidence: Score 0.25, Convert internal SearchResponse to API model.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for FinalResponse
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->