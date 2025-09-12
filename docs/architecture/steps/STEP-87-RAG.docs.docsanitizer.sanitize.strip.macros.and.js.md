# RAG STEP 87 — DocSanitizer.sanitize Strip macros and JS (RAG.docs.docsanitizer.sanitize.strip.macros.and.js)

**Type:** process  
**Category:** docs  
**Node ID:** `DocSecurity`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocSecurity` (DocSanitizer.sanitize Strip macros and JS).

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
  `RAG STEP 87 (RAG.docs.docsanitizer.sanitize.strip.macros.and.js): DocSanitizer.sanitize Strip macros and JS | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/core/security/api_key_rotation.py:16 — app.core.security.api_key_rotation.APIKeyRotationManager.__init__ (score 0.25)
   Evidence: Score 0.25, Initialize API key rotation manager.
2) app/core/security/api_key_rotation.py:23 — app.core.security.api_key_rotation.APIKeyRotationManager.generate_api_key (score 0.25)
   Evidence: Score 0.25, Generate a new API key for a user.

Args:
    user_id: User identifier
    key_t...
3) app/core/security/api_key_rotation.py:67 — app.core.security.api_key_rotation.APIKeyRotationManager.hash_api_key (score 0.25)
   Evidence: Score 0.25, Create hash of API key for secure storage.

Args:
    api_key: Raw API key
    
...
4) app/core/security/audit_logger.py:72 — app.core.security.audit_logger.SecurityAuditLogger.__init__ (score 0.25)
   Evidence: Score 0.25, Initialize security audit logger.
5) app/core/security/audit_logger.py:454 — app.core.security.audit_logger.SecurityAuditLogger._anonymize_user_id (score 0.25)
   Evidence: Score 0.25, Anonymize user ID for privacy.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DocSecurity
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->