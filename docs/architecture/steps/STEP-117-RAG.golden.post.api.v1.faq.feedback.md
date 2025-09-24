# RAG STEP 117 — POST /api/v1/faq/feedback (RAG.golden.post.api.v1.faq.feedback)

**Type:** process  
**Category:** golden  
**Node ID:** `FAQFeedback`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FAQFeedback` (POST /api/v1/faq/feedback).

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
  `RAG STEP 117 (RAG.golden.post.api.v1.faq.feedback): POST /api/v1/faq/feedback | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🟡  |  Confidence: 0.55

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.55)
   Evidence: Score 0.55, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.55)
   Evidence: Score 0.55, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.55)
   Evidence: Score 0.55, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
4) app/api/v1/faq.py:187 — app.api.v1.faq.submit_feedback (score 0.54)
   Evidence: Score 0.54, Submit user feedback on FAQ responses.

Feedback is used to improve FAQ quality ...
5) app/api/v1/faq.py:77 — app.api.v1.faq.FAQFeedbackRequest (score 0.51)
   Evidence: Score 0.51, Request model for FAQ feedback.

Notes:
- Partial implementation identified

Suggested next TDD actions:
- Complete partial implementation
- Add missing error handling
- Expand test coverage
- Add performance benchmarks if needed
<!-- AUTO-AUDIT:END -->