# RAG STEP 5 — Return 400 Bad Request (RAG.platform.return.400.bad.request)

**Type:** error  
**Category:** platform  
**Node ID:** `Error400`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Error400` (Return 400 Bad Request).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:**
  - `app/orchestrators/platform.py:412` - `step_5__error400()` (orchestrator)
- **Status:** ✅ Implemented (Internal - NOT wired by design)
- **Behavior notes:**
  - **Why Internal?** This is an error termination handler, not a workflow node. It's invoked by Step 3 (ValidCheck) when validation fails, formats the error response, and terminates the request.
  - **Why NOT wired?** Error handlers are infrastructure boundaries. The graph handles errors through exception handling and orchestrator return values, not explicit error nodes in the graph topology.
  - **Canonical Node Set:** Per `docs/architecture/RAG-architecture-mode.md`, error nodes remain Internal. Phase 6 Request/Privacy lane only wires the success path (1→3→4→6→7→9→10→8).
  - **Flow:** Step 3 (ValidCheck) decision node routes invalid requests to `step_5__error400()` which returns structured error data to the API layer for HTTP 400 response.

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
Role: Internal  |  Status: ✅ Implemented (NOT wired by design)  |  Confidence: 1.00

Top candidates:
1. app/orchestrators/platform.py:412 — step_5__error400() (score 1.00)
   Evidence: Error handler orchestrator - formats and returns HTTP 400 Bad Request

Notes:
- **Intentionally NOT wired:** Step 5 is an error termination handler, not a graph node
- **Architecture decision:** Error handlers remain Internal per canonical node set
- **Flow:** Step 3 (ValidCheck) → on validation failure → calls step_5__error400() → terminates with HTTP 400
- **Phase 6 scope:** Only success path wired (1→3→4→6→7→9→10→8), error branches stay Internal
- Step 5 represents infrastructure (error formatting), not workflow logic

Why NOT wired:
- Error termination nodes end the workflow and return HTTP responses
- LangGraph handles errors through orchestrator return values and exception handling, not explicit error nodes
- Wiring error handlers would complicate graph topology without adding observability value
- Error metrics captured at decision points (Step 3) and API layer, not in separate nodes
- Per RAG-architecture-mode.md: "Everything not listed [in canonical node set] remains Internal"

Error handling pattern:
- Step 3 (ValidCheck) decision: valid=True → Step 4 (GDPRLog), valid=False → step_5__error400() → return error to API
- Orchestrator exists and works correctly; no node wrapper needed
- HTTP layer translates orchestrator error result into FastAPI HTTPException with 400 status

Suggested next TDD actions:
- Verify Step 3 error path unit tests exist
- Confirm HTTP 400 integration tests cover validation failure scenarios
- Validate error response format matches API contract
<!-- AUTO-AUDIT:END -->