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
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.26)
   Evidence: Score 0.26, Validate the citation.
2) version-management/core/version_schema.py:140 — version-management.core.version_schema.ServiceVersion.is_valid_version (score 0.26)
   Evidence: Score 0.26, Validate if a version string follows our versioning scheme.
3) app/models/cassazione_data.py:279 — app.models.cassazione_data.ScrapingResult.is_valid (score 0.26)
   Evidence: Score 0.26, Validate the result.
4) app/models/ccnl_data.py:389 — app.models.ccnl_data.SalaryTable.is_valid_on (score 0.26)
   Evidence: Score 0.26, Check if salary table is valid on a specific date.
5) app/models/ccnl_data.py:682 — app.models.ccnl_data.CCNLAgreement.is_currently_valid (score 0.26)
   Evidence: Score 0.26, Check if CCNL is currently valid.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for AttachOK
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->