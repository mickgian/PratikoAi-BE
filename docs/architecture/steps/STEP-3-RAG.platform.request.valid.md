# RAG STEP 3 — Request valid? (RAG.platform.request.valid)

**Type:** decision  
**Category:** platform  
**Node ID:** `ValidCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidCheck` (Request valid?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:319` - `step_3__valid_check()`
- **Status:** ✅ Implemented
- **Behavior notes:** Decision orchestrator evaluating request validation results from Step 1. Returns boolean decision and routes to Step 4 (GDPRLog) if valid or Step 5 (Error400) if invalid.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (request validation flow and validation success routing)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 3 (RAG.platform.request.valid): Request valid? | attrs={request_id, validation_status, user_id}`
- [x] Feature flag / config if needed (validation rules configuration and bypass options)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/platform.py:319 — app.orchestrators.platform.step_3__valid_check (score 0.31)
   Evidence: Score 0.31, RAG STEP 3 — Request valid?
ID: RAG.platform.request.valid
Type: decision | Cate...
2) app/orchestrators/preflight.py:681 — app.orchestrators.preflight.step_85__valid_attachments_check (score 0.30)
   Evidence: Score 0.30, RAG STEP 85 — Valid attachments?
ID: RAG.preflight.valid.attachments
Type: decis...
3) app/core/security/request_signing.py:148 — app.core.security.request_signing.RequestSigner._is_timestamp_valid (score 0.29)
   Evidence: Score 0.29, Check if timestamp is within acceptable range.

Args:
    timestamp_str: Unix ti...
4) app/api/v1/api.py:64 — app.api.v1.api.health_check (score 0.27)
   Evidence: Score 0.27, Health check endpoint.

Returns:
    dict: Health status information.
5) app/main.py:157 — app.main.health_check (score 0.27)
   Evidence: Score 0.27, Health check endpoint with environment-specific information.

Returns:
    Dict[...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->