# RAG STEP 83 — FAQTool.faq_query Query Golden Set (RAG.golden.faqtool.faq.query.query.golden.set)

**Type:** process  
**Category:** golden  
**Node ID:** `FAQQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FAQQuery` (FAQTool.faq_query Query Golden Set).

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
  `RAG STEP 83 (RAG.golden.faqtool.faq.query.query.golden.set): FAQTool.faq_query Query Golden Set | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.37

Top candidates:
1) app/api/v1/faq.py:77 — app.api.v1.faq.FAQFeedbackRequest (score 0.37)
   Evidence: Score 0.37, Request model for FAQ feedback.
2) app/models/faq.py:112 — app.models.faq.FAQUsageLog (score 0.37)
   Evidence: Score 0.37, Log of FAQ usage for analytics, billing, and user feedback.
3) app/models/faq.py:486 — app.models.faq.generate_faq_cache_key (score 0.36)
   Evidence: Score 0.36, Generate cache key for FAQ variations.
4) app/models/faq.py:495 — app.models.faq.calculate_cost_savings (score 0.36)
   Evidence: Score 0.36, Calculate cost savings from FAQ system usage.
5) app/models/quality_analysis.py:27 — app.models.quality_analysis.FeedbackType (score 0.33)
   Evidence: Score 0.33, Types of expert feedback

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->