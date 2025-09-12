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
Status: ❌  |  Confidence: 0.23

Top candidates:
1) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.23)
   Evidence: Score 0.23, Convert internal SearchResponse to API model.
2) app/api/v1/data_export.py:69 — app.api.v1.data_export.CreateExportRequest.validate_future_dates (score 0.23)
   Evidence: Score 0.23, method: validate_future_dates
3) app/api/v1/data_export.py:75 — app.api.v1.data_export.CreateExportRequest.validate_date_range (score 0.23)
   Evidence: Score 0.23, method: validate_date_range
4) app/api/v1/data_sources.py:1366 — app.api.v1.data_sources._analyze_precedent_distribution (score 0.23)
   Evidence: Score 0.23, Analyze distribution of precedent values in decisions.
5) app/api/v1/data_sources.py:1375 — app.api.v1.data_sources._analyze_temporal_distribution (score 0.23)
   Evidence: Score 0.23, Analyze temporal distribution of decisions.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for PIICheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->