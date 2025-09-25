# RAG STEP 117 — POST /api/v1/faq/feedback (RAG.golden.post.api.v1.faq.feedback)

**Type:** process
**Category:** golden
**Node ID:** `FAQFeedback`

## Intent (Blueprint)
Processes FAQ feedback submissions when users provide feedback on FAQ responses. Collects user feedback (helpful/not helpful, comments, followup needed) and routes to ExpertFeedbackCollector for further processing. This step is derived from the Mermaid node: `FAQFeedback` (POST /api/v1/faq/feedback).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_117__faqfeedback`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that uses IntelligentFAQService to collect feedback on FAQ responses. Extracts feedback data from context (usage_log_id, was_helpful, followup_needed, comments), calls service to record feedback, and routes to ExpertFeedbackCollector (Step 119) with feedback metadata.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing service behavior

## TDD Task List
- [x] Unit tests (process feedback, missing usage log, invalid data, context preservation, service errors, logging)
- [x] Integration tests (FeedbackTypeSel→FAQFeedback→ExpertFeedbackCollector flow, data preparation for expert collector)
- [x] Parity tests (feedback collection behavior verification)
- [x] Implementation changes (async orchestrator wrapping IntelligentFAQService.collect_feedback)
- [x] Observability: add structured log line
  `RAG STEP 117 (RAG.golden.post.api.v1.faq.feedback): POST /api/v1/faq/feedback | attrs={usage_log_id, was_helpful, followup_needed, success, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing service)
- [x] Rollout plan (implemented with comprehensive tests)

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
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.55)
   Evidence: Score 0.55, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
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