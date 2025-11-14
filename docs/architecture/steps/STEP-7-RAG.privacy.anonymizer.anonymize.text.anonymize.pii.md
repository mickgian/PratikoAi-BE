# RAG STEP 7 — Anonymizer.anonymize_text Anonymize PII (RAG.privacy.anonymizer.anonymize.text.anonymize.pii)

**Type:** process  
**Category:** privacy  
**Node ID:** `AnonymizeText`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AnonymizeText` (Anonymizer.anonymize_text Anonymize PII).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/privacy.py:371` - `step_7__anonymize_text()`
- **Status:** 🔌
- **Behavior notes:** Internal transform within AnonymizeText node; anonymizes PII using PIIAnonymizer service.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing privacy infrastructure

## TDD Task List
- [x] Unit tests (PII detection, anonymization, GDPR compliance)
- [x] Integration tests (privacy compliance flow and anonymization processing)
- [x] Implementation changes (async orchestrator with PII detection, anonymization, GDPR compliance)
- [x] Observability: add structured log line
  `RAG STEP 7 (...): ... | attrs={pii_detected, anonymization_method, compliance_status}`
- [x] Feature flag / config if needed (privacy settings and anonymization rules)
- [x] Rollout plan (implemented with privacy compliance and data protection safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_7
- Incoming edges: [6]
- Outgoing edges: [9]

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->