# RAG STEP 129 — GoldenSet.publish_or_update versioned entry (RAG.golden.goldenset.publish.or.update.versioned.entry)

**Type:** process  
**Category:** golden  
**Node ID:** `PublishGolden`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PublishGolden` (GoldenSet.publish_or_update versioned entry).

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
  `RAG STEP 129 (RAG.golden.goldenset.publish.or.update.versioned.entry): GoldenSet.publish_or_update versioned entry | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.45

Top candidates:
1) app/models/faq.py:486 — app.models.faq.generate_faq_cache_key (score 0.45)
   Evidence: Score 0.45, Generate cache key for FAQ variations.
2) app/models/faq.py:495 — app.models.faq.calculate_cost_savings (score 0.45)
   Evidence: Score 0.45, Calculate cost savings from FAQ system usage.
3) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.40)
   Evidence: Score 0.40, Request model for FAQ queries.
4) app/api/v1/faq.py:47 — app.api.v1.faq.FAQQueryResponse (score 0.40)
   Evidence: Score 0.40, Response model for FAQ queries.
5) app/api/v1/faq.py:60 — app.api.v1.faq.FAQCreateRequest (score 0.40)
   Evidence: Score 0.40, Request model for creating FAQ entries.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->