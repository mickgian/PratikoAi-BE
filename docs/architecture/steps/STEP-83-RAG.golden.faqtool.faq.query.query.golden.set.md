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
Status: 🔌  |  Confidence: 0.51

Top candidates:
1) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
2) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.50)
   Evidence: Score 0.50, Request model for FAQ queries.
3) app/api/v1/faq.py:47 — app.api.v1.faq.FAQQueryResponse (score 0.50)
   Evidence: Score 0.50, Response model for FAQ queries.
4) app/orchestrators/golden.py:122 — app.orchestrators.golden.step_83__faqquery (score 0.50)
   Evidence: Score 0.50, RAG STEP 83 — FAQTool.faq_query Query Golden Set
ID: RAG.golden.faqtool.faq.quer...
5) app/api/v1/faq.py:1 — app.api.v1.faq (score 0.49)
   Evidence: Score 0.49, FAQ API endpoints for the Intelligent FAQ System.

This module provides REST API...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->