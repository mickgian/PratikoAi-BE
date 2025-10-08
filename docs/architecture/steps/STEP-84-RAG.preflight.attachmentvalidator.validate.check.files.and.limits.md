# RAG STEP 84 — AttachmentValidator.validate Check files and limits (RAG.preflight.attachmentvalidator.validate.check.files.and.limits)

**Type:** process  
**Category:** preflight  
**Node ID:** `ValidateAttach`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidateAttach` (AttachmentValidator.validate Check files and limits).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/preflight.py:597` - `step_84__validate_attachments()`
- **Status:** 🔌
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
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->