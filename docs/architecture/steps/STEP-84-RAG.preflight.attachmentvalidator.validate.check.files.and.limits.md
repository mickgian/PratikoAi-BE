# RAG STEP 84 — AttachmentValidator.validate Check files and limits (RAG.preflight.attachmentvalidator.validate.check.files.and.limits)

**Type:** process  
**Category:** preflight  
**Node ID:** `ValidateAttach`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidateAttach` (AttachmentValidator.validate Check files and limits).

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
  `RAG STEP 84 (RAG.preflight.attachmentvalidator.validate.check.files.and.limits): AttachmentValidator.validate Check files and limits | attrs={...}`
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
1) app/orchestrators/preflight.py:91 — app.orchestrators.preflight.step_19__attach_check (score 0.27)
   Evidence: Score 0.27, RAG STEP 19 — Attachments present?
ID: RAG.preflight.attachments.present
Type: p...
2) validate_italian_implementation.py:8 — validate_italian_implementation.check_file_exists (score 0.27)
   Evidence: Score 0.27, Check if a file exists and return status.
3) validate_italian_implementation.py:19 — validate_italian_implementation.check_file_content (score 0.27)
   Evidence: Score 0.27, Check if a file contains expected content.
4) validate_payment_implementation.py:8 — validate_payment_implementation.check_file_exists (score 0.27)
   Evidence: Score 0.27, Check if a file exists and return status.
5) validate_payment_implementation.py:19 — validate_payment_implementation.check_file_content (score 0.27)
   Evidence: Score 0.27, Check if a file contains expected content.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ValidateAttach
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->