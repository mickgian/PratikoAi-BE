# RAG STEP 127 — GoldenSetUpdater.propose_candidate from expert feedback (RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback)

**Type:** process
**Category:** golden
**Node ID:** `GoldenCandidate`

## Intent (Blueprint)
Proposes a new FAQ candidate for the Golden Set based on expert feedback. When an expert provides improved answers and corrections, this step transforms that feedback into a structured FAQ candidate with priority scoring, quality metrics, and regulatory references. The candidate is then routed to GoldenApproval (Step 128) for approval decision. This step is derived from the Mermaid node: `GoldenCandidate` (GoldenSetUpdater.propose_candidate from expert feedback).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_127__golden_candidate`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that transforms expert feedback into FAQ candidate. Extracts expert feedback data (query, answer, category, regulatory refs, confidence), calculates priority score based on confidence × trust × frequency, derives quality score from expert metrics, and routes to GoldenApproval (Step 128) with candidate metadata.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing workflow

## TDD Task List
- [x] Unit tests (propose candidate, priority calculation, regulatory refs preservation, context preservation, metadata, missing category, error handling, logging)
- [x] Parity tests (candidate creation behavior verification)
- [x] Integration tests (DetermineAction→GoldenCandidate→GoldenApproval flow, data preparation for approval)
- [x] Implementation changes (async orchestrator creating FAQ candidate from expert feedback)
- [x] Observability: add structured log line
  `RAG STEP 127 (RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback): GoldenSetUpdater.propose_candidate from expert feedback | attrs={candidate_id, priority_score, quality_score, expert_confidence, category, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing workflow)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.53

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.53)
   Evidence: Score 0.53, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.53)
   Evidence: Score 0.53, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq.py:187 — app.api.v1.faq.submit_feedback (score 0.50)
   Evidence: Score 0.50, Submit user feedback on FAQ responses.

Feedback is used to improve FAQ quality ...
5) app/api/v1/faq_automation.py:303 — app.api.v1.faq_automation.generate_faqs_from_candidates (score 0.49)
   Evidence: Score 0.49, Generate FAQs from selected candidates

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->