# RAG STEP 2 — User submits query via POST /api/v1/chat (RAG.platform.user.submits.query.via.post.api.v1.chat)

**Type:** startEnd  
**Category:** platform  
**Node ID:** `Start`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Start` (User submits query via POST /api/v1/chat).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/platform.py:179` - `step_2__start()`, `app/api/v1/chatbot.py:40` - `@router.post("/chat")`
- **Status:** missing
- **Behavior notes:** Internal transform within Start node; extracts chat request from POST endpoint.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (POST endpoint flow and orchestrator integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 2 (RAG.platform.user.submits.query.via.post.api.v1.chat): User submits query via POST /api/v1/chat | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (API endpoint configuration and rate limiting)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: ❌ (Missing)  |  Confidence: 0.28

Top candidates:
1) app/api/v1/chatbot.py:42 — app.api.v1.chatbot.chat (score 0.28)
   Evidence: Score 0.28, Process a chat request using LangGraph.

Args:
    request: The FastAPI request ...
2) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.28)
   Evidence: Score 0.28, Query the FAQ system with semantic search and response variation.

This endpoint...
3) app/api/v1/auth.py:157 — app.api.v1.auth.register_user (score 0.28)
   Evidence: Score 0.28, Register a new user.

Args:
    request: The FastAPI request object for rate lim...
4) app/api/v1/auth.py:463 — app.api.v1.auth.logout_user (score 0.28)
   Evidence: Score 0.28, Logout a user by revoking their refresh token.

This endpoint revokes the user's...
5) app/api/v1/chatbot.py:111 — app.api.v1.chatbot.chat_stream (score 0.28)
   Evidence: Score 0.28, Process a chat request using LangGraph with streaming response.

Args:
    reque...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create startEnd implementation for Start
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->