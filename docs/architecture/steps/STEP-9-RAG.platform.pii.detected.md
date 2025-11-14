# RAG STEP 9 — PII detected? (RAG.platform.pii.detected)

**Type:** decision  
**Category:** platform  
**Node ID:** `PIICheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PIICheck` (PII detected?).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/platform.py:565` - `step_9__piicheck()`
- **Status:** ✅
- **Behavior notes:** Node orchestrator detecting personally identifiable information in user requests. Coordinates PII detection analysis and confidence scoring for privacy compliance.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (PII detection flow and privacy compliance routing)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 9 (RAG.platform.pii.detected): PII detected? | attrs={request_id, pii_detected, confidence_score}`
- [x] Feature flag / config if needed (PII detection thresholds and privacy settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_9
- Incoming edges: [7]
- Outgoing edges: [10]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->