# RAG STEP 84 — AttachmentValidator.validate Check files and limits (RAG.preflight.attachmentvalidator.validate.check.files.and.limits)

**Type:** process  
**Category:** preflight  
**Node ID:** `ValidateAttach`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidateAttach` (AttachmentValidator.validate Check files and limits).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/preflight.py:597` - `step_84__validate_attachments()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator validating attachments against file size limits and supported types. Checks file formats, sizes, and security constraints.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing preflight validation infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 84 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/orchestrators/preflight.py:92 — app.orchestrators.preflight.step_19__attach_check (score 0.27)
   Evidence: Score 0.27, RAG STEP 19 — Attachments present?
ID: RAG.preflight.attachments.present
Type: p...
2) validate_italian_implementation.py:8 — validate_italian_implementation.check_file_exists (score 0.27)
   Evidence: Score 0.27, Check if a file exists and return status.
3) validate_italian_implementation.py:19 — validate_italian_implementation.check_file_content (score 0.27)
   Evidence: Score 0.27, Check if a file contains expected content.
4) validate_payment_implementation.py:8 — validate_payment_implementation.check_file_exists (score 0.27)
   Evidence: Score 0.27, Check if a file exists and return status.
5) validate_payment_implementation.py:19 — validate_payment_implementation.check_file_content (score 0.27)
   Evidence: Score 0.27, Check if a file contains expected content.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ValidateAttach
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->