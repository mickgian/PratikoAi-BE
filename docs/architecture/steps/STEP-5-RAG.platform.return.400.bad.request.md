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
- **Status:** 🔌
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
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->