# RAG STEP 6 — PRIVACY_ANONYMIZE_REQUESTS enabled? (RAG.privacy.privacy.anonymize.requests.enabled)

**Type:** decision  
**Category:** privacy  
**Node ID:** `PrivacyCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PrivacyCheck` (PRIVACY_ANONYMIZE_REQUESTS enabled?).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/privacy.py:187` - `step_6__privacy_check()`
- **Status:** missing
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
Status: missing  |  Confidence: 0.48

Top candidates:
1) app/core/privacy/anonymizer.py:281 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_text (score 0.48)
   Evidence: Score 0.48, Anonymize PII in text while preserving structure.
2) app/core/privacy/anonymizer.py:322 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_structured_data (score 0.47)
   Evidence: Score 0.47, Anonymize PII in structured data (dictionaries).
3) app/orchestrators/privacy.py:371 — app.orchestrators.privacy.step_7__anonymize_text (score 0.47)
   Evidence: Score 0.47, RAG STEP 7 — Anonymizer.anonymize_text Anonymize PII
ID: RAG.privacy.anonymizer....
4) app/models/encrypted_user.py:246 — app.models.encrypted_user.EncryptedUser.anonymize_for_gdpr_deletion (score 0.46)
   Evidence: Score 0.46, Anonymize user data for GDPR "right to be forgotten" compliance.

Replaces PII w...
5) app/core/privacy/gdpr.py:465 — app.core.privacy.gdpr.GDPRCompliance.__init__ (score 0.42)
   Evidence: Score 0.42, Initialize GDPR compliance system.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test PII detection and anonymization
<!-- AUTO-AUDIT:END -->