# RAG STEP 7 — Anonymizer.anonymize_text Anonymize PII (RAG.privacy.anonymizer.anonymize.text.anonymize.pii)

**Type:** process  
**Category:** privacy  
**Node ID:** `AnonymizeText`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AnonymizeText` (Anonymizer.anonymize_text Anonymize PII).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/privacy.py:371` - `step_7__anonymize_text()`
- **Status:** missing
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.56

Top candidates:
1) app/core/privacy/anonymizer.py:281 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_text (score 0.56)
   Evidence: Score 0.56, Anonymize PII in text while preserving structure.
2) app/orchestrators/privacy.py:371 — app.orchestrators.privacy.step_7__anonymize_text (score 0.51)
   Evidence: Score 0.51, RAG STEP 7 — Anonymizer.anonymize_text Anonymize PII
ID: RAG.privacy.anonymizer....
3) app/core/privacy/anonymizer.py:322 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_structured_data (score 0.51)
   Evidence: Score 0.51, Anonymize PII in structured data (dictionaries).
4) app/models/encrypted_user.py:246 — app.models.encrypted_user.EncryptedUser.anonymize_for_gdpr_deletion (score 0.46)
   Evidence: Score 0.46, Anonymize user data for GDPR "right to be forgotten" compliance.

Replaces PII w...
5) app/api/v1/privacy.py:38 — app.api.v1.privacy.anonymize_text (score 0.46)
   Evidence: Score 0.46, Anonymize PII in text.

Args:
    request: FastAPI request object
    anonymizat...

Notes:
- Partial implementation identified

Suggested next TDD actions:
- Complete partial implementation
- Add missing error handling
- Expand test coverage
- Add performance benchmarks if needed
- Test PII detection and anonymization
<!-- AUTO-AUDIT:END -->