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
Status: 🔌  |  Confidence: 0.55

Top candidates:
1) app/core/privacy/anonymizer.py:281 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_text (score 0.55)
   Evidence: Score 0.55, Anonymize PII in text while preserving structure.
2) app/core/privacy/anonymizer.py:322 — app.core.privacy.anonymizer.PIIAnonymizer.anonymize_structured_data (score 0.51)
   Evidence: Score 0.51, Anonymize PII in structured data (dictionaries).
3) app/core/privacy/anonymizer.py:55 — app.core.privacy.anonymizer.PIIAnonymizer.__init__ (score 0.46)
   Evidence: Score 0.46, Initialize the anonymizer with Italian-specific patterns.
4) app/core/privacy/anonymizer.py:61 — app.core.privacy.anonymizer.PIIAnonymizer._build_patterns (score 0.46)
   Evidence: Score 0.46, Build regex patterns for PII detection.
5) app/core/privacy/anonymizer.py:134 — app.core.privacy.anonymizer.PIIAnonymizer._generate_anonymous_replacement (score 0.46)
   Evidence: Score 0.46, Generate consistent anonymous replacement for PII.

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test PII detection and anonymization
<!-- AUTO-AUDIT:END -->