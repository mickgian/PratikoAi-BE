# RAG STEP 85 — Valid attachments? (RAG.preflight.valid.attachments)

**Type:** decision  
**Category:** preflight  
**Node ID:** `AttachOK`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AttachOK` (Valid attachments?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/preflight.py:681` - `step_85__valid_attachments_check()`
- **Role:** Node
- **Status:** missing
- **Behavior notes:** Async orchestrator verifying attachments passed validation checks. Decision point routing to document processing or error handling.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing preflight validation infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 85 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/preflight.py:681 — app.orchestrators.preflight.step_85__valid_attachments_check (score 0.30)
   Evidence: Score 0.30, RAG STEP 85 — Valid attachments?
ID: RAG.preflight.valid.attachments
Type: decis...
2) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.26)
   Evidence: Score 0.26, Validate the citation.
3) app/orchestrators/platform.py:319 — app.orchestrators.platform.step_3__valid_check (score 0.26)
   Evidence: Score 0.26, RAG STEP 3 — Request valid?
ID: RAG.platform.request.valid
Type: decision | Cate...
4) app/orchestrators/preflight.py:92 — app.orchestrators.preflight.step_19__attach_check (score 0.26)
   Evidence: Score 0.26, RAG STEP 19 — Attachments present?
ID: RAG.preflight.attachments.present
Type: p...
5) app/orchestrators/preflight.py:597 — app.orchestrators.preflight.step_84__validate_attachments (score 0.26)
   Evidence: Score 0.26, RAG STEP 84 — AttachmentValidator.validate Check files and limits
ID: RAG.prefli...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for AttachOK
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->