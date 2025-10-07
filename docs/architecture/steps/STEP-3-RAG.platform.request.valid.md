# RAG STEP 3 — Request valid? (RAG.platform.request.valid)

**Type:** decision  
**Category:** platform  
**Node ID:** `ValidCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidCheck` (Request valid?).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** ✅ (Implemented & Wired)
- **Paths / classes:**
  - app/core/langgraph/nodes/step_003__valid_check.py:13 — node_step_3 (wrapper)
  - app/orchestrators/platform.py:319 (orchestrator)
- **Behavior notes:**
  - Runtime boundary; decision point for request validation.
  - Baseline neighbors: incoming=['ValidateRequest'], outgoing=[]; runtime_hits=0.

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
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 1.00

Top candidates:
1) app/core/langgraph/nodes/step_003__valid_check.py:13 — node_step_3 (score 1.00)
   Evidence: Node wrapper delegating to orchestrator with rag_step_log and rag_step_timer

Notes:
- Wired via graph registry ✅
- Incoming: [1], Outgoing: [4]
- Phase 6 Request/Privacy lane implemented

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->