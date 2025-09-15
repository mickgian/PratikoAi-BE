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
Status: 🔌  |  Confidence: 0.39

Top candidates:
1) app/core/privacy/__init__.py:1 — app.core.privacy.__init__ (score 0.39)
   Evidence: Score 0.39, Privacy and GDPR compliance utilities.
2) app/models/encrypted_user.py:246 — app.models.encrypted_user.EncryptedUser.anonymize_for_gdpr_deletion (score 0.36)
   Evidence: Score 0.36, Anonymize user data for GDPR "right to be forgotten" compliance.

Replaces PII w...
3) app/schemas/privacy.py:221 — app.schemas.privacy.validate_pii_type (score 0.32)
   Evidence: Score 0.32, Validate PII type string.
4) app/core/security/audit_logger.py:454 — app.core.security.audit_logger.SecurityAuditLogger._anonymize_user_id (score 0.31)
   Evidence: Score 0.31, Anonymize user ID for privacy.
5) app/api/v1/privacy.py:1 — app.api.v1.privacy (score 0.31)
   Evidence: Score 0.31, Privacy and GDPR compliance API endpoints.

This module provides endpoints for p...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test PII detection and anonymization
<!-- AUTO-AUDIT:END -->