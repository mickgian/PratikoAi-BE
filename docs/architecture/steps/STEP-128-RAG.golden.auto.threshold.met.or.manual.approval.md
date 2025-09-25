# RAG STEP 128 — Auto threshold met or manual approval? (RAG.golden.auto.threshold.met.or.manual.approval)

**Type:** decision
**Category:** golden
**Node ID:** `GoldenApproval`

## Intent (Blueprint)
Decision node that determines if an FAQ candidate meets the auto-approval quality threshold or requires manual review. Evaluates candidate quality score against configured thresholds (auto_approve_threshold: 0.95, quality_threshold: 0.85). Routes approved candidates to PublishGolden (Step 129) for immediate publication, and rejected/manual review candidates to FeedbackEnd (Step 115). This step is derived from the Mermaid node: `GoldenApproval` (Auto threshold met or manual approval?).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_128__golden_approval`
- **Status:** ✅ Implemented
- **Behavior notes:** Async decision orchestrator that evaluates FAQ candidate quality score. Auto-approves if quality_score >= 0.95, rejects if < 0.85, requires manual review if between thresholds. Uses FAQ_AUTOMATION_CONFIG for threshold values. Routes to 'publish_golden' (Step 129) if approved, or 'feedback_end' (Step 115) if rejected/manual review needed.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing workflow

## TDD Task List
- [x] Unit tests (auto-approve high quality, reject low quality, manual review borderline, trust score consideration, context preservation, approval metadata, missing score, error handling, logging)
- [x] Parity tests (approval logic behavior verification)
- [x] Integration tests (GoldenCandidate→GoldenApproval→PublishGolden flow, rejection routing to FeedbackEnd)
- [x] Implementation changes (async decision orchestrator with threshold-based routing)
- [x] Observability: add structured log line
  `RAG STEP 128 (RAG.golden.auto.threshold.met.or.manual.approval): Auto threshold met or manual approval? | attrs={approval_decision, quality_score, trust_score, threshold, next_step, processing_stage}`
- [x] Feature flag / config if needed (uses FAQ_AUTOMATION_CONFIG for thresholds)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ✅  |  Confidence: 1.00

Implementation:
- app/orchestrators/golden.py:733 — step_128__golden_approval (async decision orchestrator)
- tests/test_rag_step_128_golden_approval.py — 13 comprehensive tests (all passing)

Key Features:
- Async decision orchestrator evaluating FAQ candidate quality
- Threshold-based approval logic:
  * Auto-approve: quality_score >= 0.95 → publish_golden (Step 129)
  * Reject: quality_score < 0.85 → feedback_end (Step 115)
  * Manual review: 0.85 <= quality_score < 0.95 → feedback_end (for now)
- Uses FAQ_AUTOMATION_CONFIG for configurable thresholds
- Structured logging with rag_step_log (step 128, processing stages)
- Context preservation (expert_id, trust_score, user/session data)
- Approval metadata tracking (decided_at, decision, quality_score, threshold_used)
- Error handling with graceful degradation (rejects on error for safety)
- Routes to correct next step based on decision

Test Coverage:
- Unit: auto-approve high quality, reject low quality, manual review borderline, trust score consideration, context preservation, approval metadata, missing score, error handling, logging
- Parity: approval logic behavior verification
- Integration: GoldenCandidate→GoldenApproval→PublishGolden flow, rejection routing to FeedbackEnd

Decision Logic:
- quality_score >= 0.95 → auto_approved → publish_golden
- quality_score < 0.85 → rejected → feedback_end
- 0.85 <= quality_score < 0.95 → manual_review_required → feedback_end

Notes:
- Full implementation complete following MASTER_GUARDRAILS
- Thin orchestrator pattern (no business logic)
- All TDD tasks completed
<!-- AUTO-AUDIT:END -->