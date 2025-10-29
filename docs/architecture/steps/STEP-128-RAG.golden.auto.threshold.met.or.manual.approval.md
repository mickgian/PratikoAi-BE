# RAG STEP 128 — Auto threshold met or manual approval? (RAG.golden.auto.threshold.met.or.manual.approval)

**Type:** decision
**Category:** golden
**Node ID:** `GoldenApproval`

## Intent (Blueprint)
Decision node that determines if an FAQ candidate meets the auto-approval quality threshold or requires manual review. Evaluates candidate quality score against configured thresholds (auto_approve_threshold: 0.95, quality_threshold: 0.85). Routes approved candidates to PublishGolden (Step 129) for immediate publication, and rejected/manual review candidates to FeedbackEnd (Step 115). This step is derived from the Mermaid node: `GoldenApproval` (Auto threshold met or manual approval?).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:step_128__golden_approval`
- **Status:** 🔌
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->