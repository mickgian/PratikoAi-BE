# RAG STEP 124 — Update expert metrics (RAG.metrics.update.expert.metrics)

**Type:** process  
**Category:** metrics  
**Node ID:** `UpdateExpertMetrics`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `UpdateExpertMetrics` (Update expert metrics).

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
  `RAG STEP 124 (RAG.metrics.update.expert.metrics): Update expert metrics | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) evals/helpers.py:92 — evals.helpers.update_success_metrics (score 0.32)
   Evidence: Score 0.32, Update metrics for a successful evaluation.

Args:
    report: The report dictio...
2) evals/helpers.py:114 — evals.helpers.update_failure_metrics (score 0.32)
   Evidence: Score 0.32, Update metrics for a failed evaluation.

Args:
    report: The report dictionary...
3) app/core/monitoring/metrics.py:353 — app.core.monitoring.metrics.update_system_metrics (score 0.31)
   Evidence: Score 0.31, Update system-level metrics like memory and CPU usage.
4) app/core/monitoring/metrics.py:426 — app.core.monitoring.metrics.update_subscription_metrics (score 0.31)
   Evidence: Score 0.31, Update subscription counts.
5) app/core/monitoring/metrics.py:431 — app.core.monitoring.metrics.update_monthly_revenue (score 0.30)
   Evidence: Score 0.30, Update monthly revenue.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->