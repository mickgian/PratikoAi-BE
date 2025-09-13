# RAG STEP 128 — Auto threshold met or manual approval? (RAG.golden.auto.threshold.met.or.manual.approval)

**Type:** decision  
**Category:** golden  
**Node ID:** `GoldenApproval`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenApproval` (Auto threshold met or manual approval?).

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
  `RAG STEP 128 (RAG.golden.auto.threshold.met.or.manual.approval): Auto threshold met or manual approval? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.44

Top candidates:
1) app/models/faq.py:486 — app.models.faq.generate_faq_cache_key (score 0.44)
   Evidence: Score 0.44, Generate cache key for FAQ variations.
2) app/models/faq.py:495 — app.models.faq.calculate_cost_savings (score 0.44)
   Evidence: Score 0.44, Calculate cost savings from FAQ system usage.
3) app/models/faq.py:525 — app.models.faq.get_faq_search_vector (score 0.38)
   Evidence: Score 0.38, Generate search vector content for PostgreSQL full-text search.
4) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.37)
   Evidence: Score 0.37, Request model for FAQ queries.
5) app/api/v1/faq.py:47 — app.api.v1.faq.FAQQueryResponse (score 0.37)
   Evidence: Score 0.37, Response model for FAQ queries.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->