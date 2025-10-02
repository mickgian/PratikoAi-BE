# RAG STEP 71 — Return 500 error (RAG.platform.return.500.error)

**Type:** error  
**Category:** platform  
**Node ID:** `Error500`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Error500` (Return 500 error).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/platform.py:1674` - `step_71__error500()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator handling critical system errors by returning 500 status. Formats error response with appropriate logging and monitoring for production environment failures.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 71 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: ❌ (Missing)  |  Confidence: 0.22

Top candidates:
1) app/orchestrators/response.py:402 — app.orchestrators.response._handle_return_complete_error (score 0.22)
   Evidence: Score 0.22, Handle errors in ChatResponse formatting with graceful fallback.
2) evals/main.py:64 — evals.main.print_error (score 0.20)
   Evidence: Score 0.20, Print an error message with colors.

Args:
    message: The message to print
3) app/models/query.py:131 — app.models.query.QueryErrorResponse (score 0.19)
   Evidence: Score 0.19, Error response for failed queries.
4) app/orchestrators/platform.py:1674 — app.orchestrators.platform.step_71__error500 (score 0.19)
   Evidence: Score 0.19, RAG STEP 71 — Return 500 error
ID: RAG.platform.return.500.error
Type: error | C...
5) version-management/cli/version_cli.py:69 — version-management.cli.version_cli.VersionCLI.print_error (score 0.19)
   Evidence: Score 0.19, Print error message.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for Error500
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->