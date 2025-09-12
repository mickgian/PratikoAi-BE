# RAG STEP 3 — Request valid? (RAG.platform.request.valid)

**Type:** decision  
**Category:** platform  
**Node ID:** `ValidCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidCheck` (Request valid?).

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
  `RAG STEP 3 (RAG.platform.request.valid): Request valid? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.24

Top candidates:
1) feature-flags/feature_flag_service.py:179 — feature-flags.feature_flag_service.FlagRequest.validate_flag_id (score 0.24)
   Evidence: Score 0.24, method: validate_flag_id
2) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.24)
   Evidence: Score 0.24, Validate the citation.
3) app/models/cassazione_data.py:279 — app.models.cassazione_data.ScrapingResult.is_valid (score 0.24)
   Evidence: Score 0.24, Validate the result.
4) app/services/ccnl_service.py:91 — app.services.ccnl_service.CCNLQueryFilters.is_valid (score 0.24)
   Evidence: Score 0.24, Validate filter constraints.
5) app/core/security/request_signing.py:16 — app.core.security.request_signing.RequestSigner.__init__ (score 0.23)
   Evidence: Score 0.23, Initialize request signer.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for ValidCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->