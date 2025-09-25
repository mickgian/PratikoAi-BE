# RAG STEP 85 — Valid attachments? (RAG.preflight.valid.attachments)

**Type:** decision  
**Category:** preflight  
**Node ID:** `AttachOK`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AttachOK` (Valid attachments?).

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
  `RAG STEP 85 (RAG.preflight.valid.attachments): Valid attachments? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/preflight.py:681 — app.orchestrators.preflight.step_85__valid_attachments_check (score 0.30)
   Evidence: Score 0.30, RAG STEP 85 — Valid attachments?
ID: RAG.preflight.valid.attachments
Type: decis...
2) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.26)
   Evidence: Score 0.26, Validate the citation.
3) app/orchestrators/platform.py:319 — app.orchestrators.platform.step_3__valid_check (score 0.26)
   Evidence: Score 0.26, RAG STEP 3 — Request valid?
ID: RAG.platform.request.valid
Type: decision | Cate...
4) app/orchestrators/preflight.py:92 — app.orchestrators.preflight.step_19__attach_check (score 0.26)
   Evidence: Score 0.26, RAG STEP 19 — Attachments present?
ID: RAG.preflight.attachments.present
Type: p...
5) app/orchestrators/preflight.py:597 — app.orchestrators.preflight.step_84__validate_attachments (score 0.26)
   Evidence: Score 0.26, RAG STEP 84 — AttachmentValidator.validate Check files and limits
ID: RAG.prefli...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for AttachOK
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->