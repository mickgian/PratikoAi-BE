# RAG STEP 9 — PII detected? (RAG.platform.pii.detected)

**Type:** decision  
**Category:** platform  
**Node ID:** `PIICheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PIICheck` (PII detected?).

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
  `RAG STEP 9 (RAG.platform.pii.detected): PII detected? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/orchestrators/platform.py:563 — app.orchestrators.platform.step_9__piicheck (score 0.27)
   Evidence: Score 0.27, RAG STEP 9 — PII detected?
ID: RAG.platform.pii.detected
Type: decision | Catego...
2) app/core/logging.py:47 — app.core.logging._anonymize_pii_processor (score 0.26)
   Evidence: Score 0.26, Structlog processor to anonymize PII in log messages.
3) app/orchestrators/platform.py:661 — app.orchestrators.platform.step_10__log_pii (score 0.26)
   Evidence: Score 0.26, RAG STEP 10 — Logger.info Log PII anonymization
ID: RAG.platform.logger.info.log...
4) app/schemas/privacy.py:221 — app.schemas.privacy.validate_pii_type (score 0.26)
   Evidence: Score 0.26, Validate PII type string.
5) app/core/privacy/anonymizer.py:164 — app.core.privacy.anonymizer.PIIAnonymizer.detect_pii (score 0.26)
   Evidence: Score 0.26, Detect PII in text and return matches.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for PIICheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->