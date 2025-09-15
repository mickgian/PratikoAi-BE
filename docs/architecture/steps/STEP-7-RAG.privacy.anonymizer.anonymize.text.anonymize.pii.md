# RAG STEP 7 — Anonymizer.anonymize_text Anonymize PII (RAG.privacy.anonymizer.anonymize.text.anonymize.pii)

**Type:** process  
**Category:** privacy  
**Node ID:** `AnonymizeText`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AnonymizeText` (Anonymizer.anonymize_text Anonymize PII).

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
  `RAG STEP 7 (RAG.privacy.anonymizer.anonymize.text.anonymize.pii): Anonymizer.anonymize_text Anonymize PII | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🟡  |  Confidence: 0.56

Top candidates:
1) app/core/privacy/anonymizer.py:281 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_text (score 0.56)
   Evidence: Score 0.56, Anonymize PII in text while preserving structure.
2) app/core/privacy/anonymizer.py:322 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_structured_data (score 0.51)
   Evidence: Score 0.51, Anonymize PII in structured data (dictionaries).
3) app/models/encrypted_user.py:246 — app.models.encrypted_user.EncryptedUser.anonymize_for_gdpr_deletion (score 0.46)
   Evidence: Score 0.46, Anonymize user data for GDPR "right to be forgotten" compliance.

Replaces PII w...
4) app/core/privacy/anonymizer.py:164 — app.core.privacy.anonymizer.PIIAnonymizer.detect_pii (score 0.45)
   Evidence: Score 0.45, Detect PII in text and return matches.
5) app/core/privacy/anonymizer.py:1 — app.core.privacy.anonymizer (score 0.43)
   Evidence: Score 0.43, PII detection and anonymization utilities for GDPR compliance.

This module prov...

Notes:
- Partial implementation identified

Suggested next TDD actions:
- Complete partial implementation
- Add missing error handling
- Expand test coverage
- Add performance benchmarks if needed
- Test PII detection and anonymization
<!-- AUTO-AUDIT:END -->