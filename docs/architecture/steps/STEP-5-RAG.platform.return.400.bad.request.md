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
Status: ❌  |  Confidence: 0.14

Top candidates:
1) app/services/resilient_llm_service.py:56 — app.services.resilient_llm_service.LLMRequest (score 0.14)
   Evidence: Score 0.14, LLM request with metadata.
2) app/schemas/chat.py:81 — app.schemas.chat.ChatRequest (score 0.14)
   Evidence: Score 0.14, Request model for chat endpoint.

Attributes:
    messages: List of messages in ...
3) feature-flags/feature_flag_service.py:169 — feature-flags.feature_flag_service.FlagRequest (score 0.14)
   Evidence: Score 0.14, Request model for creating/updating flags.
4) feature-flags/feature_flag_service.py:179 — feature-flags.feature_flag_service.FlagRequest.validate_flag_id (score 0.14)
   Evidence: Score 0.14, method: validate_flag_id
5) app/models/query.py:79 — app.models.query.QueryRequest (score 0.13)
   Evidence: Score 0.13, Pydantic model for incoming query requests.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for Error400
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->