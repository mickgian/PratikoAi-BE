# RAG STEP 5 — Return 400 Bad Request (RAG.platform.return.400.bad.request)

**Type:** error  
**Category:** platform  
**Node ID:** `Error400`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Error400` (Return 400 Bad Request).

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
  `RAG STEP 5 (RAG.platform.return.400.bad.request): Return 400 Bad Request | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

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
3) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.19)
   Evidence: Score 0.19, Request model for FAQ queries.
4) app/api/v1/faq.py:60 — app.api.v1.faq.FAQCreateRequest (score 0.19)
   Evidence: Score 0.19, Request model for creating FAQ entries.
5) app/api/v1/faq.py:69 — app.api.v1.faq.FAQUpdateRequest (score 0.19)
   Evidence: Score 0.19, Request model for updating FAQ entries.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for Error400
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->