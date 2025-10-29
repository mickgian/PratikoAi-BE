# RAG STEP 117 — POST /api/v1/faq/feedback (RAG.golden.post.api.v1.faq.feedback)

**Type:** process
**Category:** golden
**Node ID:** `FAQFeedback`

## Intent (Blueprint)
Processes FAQ feedback submissions when users provide feedback on FAQ responses. Collects user feedback (helpful/not helpful, comments, followup needed) and routes to ExpertFeedbackCollector for further processing. This step is derived from the Mermaid node: `FAQFeedback` (POST /api/v1/faq/feedback).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:step_117__faqfeedback`
- **Status:** 🔌
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->