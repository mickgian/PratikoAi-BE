# RAG STEP 5 — Return 400 Bad Request (RAG.platform.return.400.bad.request)

**Type:** error  
**Category:** platform  
**Node ID:** `Error400`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Error400` (Return 400 Bad Request).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:412` - `step_5__error400()`
- **Status:** ✅ Implemented
- **Behavior notes:** Error orchestrator returning HTTP 400 Bad Request response. Formats error details and terminates RAG flow with appropriate error messaging.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (error handling flow and HTTP 400 response validation)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 5 (RAG.platform.return.400.bad.request): Return 400 Bad Request | attrs={request_id, error_type, validation_errors}`
- [x] Feature flag / config if needed (error response format configuration and debugging options)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.19

Top candidates:
1) app/models/query.py:79 — app.models.query.QueryRequest (score 0.19)
   Evidence: Score 0.19, Pydantic model for incoming query requests.
2) app/schemas/chat.py:81 — app.schemas.chat.ChatRequest (score 0.19)
   Evidence: Score 0.19, Request model for chat endpoint.

Attributes:
    messages: List of messages in ...
3) app/api/v1/data_export.py:243 — app.api.v1.data_export.request_data_export (score 0.19)
   Evidence: Score 0.19, Request a comprehensive data export.

Creates a new data export request that wil...
4) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.19)
   Evidence: Score 0.19, Request model for FAQ queries.
5) app/api/v1/faq.py:60 — app.api.v1.faq.FAQCreateRequest (score 0.19)
   Evidence: Score 0.19, Request model for creating FAQ entries.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for Error400
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->