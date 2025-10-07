# RAG STEP 6 — PRIVACY_ANONYMIZE_REQUESTS enabled? (RAG.privacy.privacy.anonymize.requests.enabled)

**Type:** decision  
**Category:** privacy  
**Node ID:** `PrivacyCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PrivacyCheck` (PRIVACY_ANONYMIZE_REQUESTS enabled?).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/privacy.py:187` - `step_6__privacy_check()`
- **Status:** ✅ (Implemented & Wired)
- **Behavior notes:** Node orchestrator checking PRIVACY_ANONYMIZE_REQUESTS configuration. Routes to Step 7 (AnonymizeText) if enabled or Step 8 (InitAgent) if disabled.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing privacy infrastructure

## TDD Task List
- [x] Unit tests (PII detection, anonymization, GDPR compliance)
- [x] Integration tests (privacy compliance flow and anonymization processing)
- [x] Implementation changes (async orchestrator with PII detection, anonymization, GDPR compliance)
- [x] Observability: add structured log line
  `RAG STEP 6 (...): ... | attrs={pii_detected, anonymization_method, compliance_status}`
- [x] Feature flag / config if needed (privacy settings and anonymization rules)
- [x] Rollout plan (implemented with privacy compliance and data protection safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 1.00

Top candidates:
1) app/core/langgraph/nodes/step_006__privacy_check.py:13 — node_step_6 (score 1.00)
   Evidence: Node wrapper delegating to orchestrator with rag_step_log and rag_step_timer

Notes:
- Wired via graph registry ✅
- Incoming: [4], Outgoing: [7]
- Phase 6 Request/Privacy lane implemented

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->