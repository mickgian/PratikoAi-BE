# RAG STEP 6 — PRIVACY_ANONYMIZE_REQUESTS enabled? (RAG.privacy.privacy.anonymize.requests.enabled)

**Type:** decision  
**Category:** privacy  
**Node ID:** `PrivacyCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PrivacyCheck` (PRIVACY_ANONYMIZE_REQUESTS enabled?).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 6 (RAG.privacy.privacy.anonymize.requests.enabled): PRIVACY_ANONYMIZE_REQUESTS enabled? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.48

Top candidates:
1) app/core/privacy/anonymizer.py:281 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_text (score 0.48)
   Evidence: Score 0.48, Anonymize PII in text while preserving structure.
2) app/core/privacy/anonymizer.py:322 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_structured_data (score 0.48)
   Evidence: Score 0.48, Anonymize PII in structured data (dictionaries).
3) app/core/privacy/gdpr.py:239 — app.core.privacy.gdpr.DataProcessor.can_process_data (score 0.45)
   Evidence: Score 0.45, Check if data processing is allowed under GDPR.
4) app/core/privacy/gdpr.py:379 — app.core.privacy.gdpr.AuditLogger._log_event (score 0.45)
   Evidence: Score 0.45, Log a GDPR audit event.
5) app/core/privacy/gdpr.py:465 — app.core.privacy.gdpr.GDPRCompliance.__init__ (score 0.45)
   Evidence: Score 0.45, Initialize GDPR compliance system.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test PII detection and anonymization
<!-- AUTO-AUDIT:END -->