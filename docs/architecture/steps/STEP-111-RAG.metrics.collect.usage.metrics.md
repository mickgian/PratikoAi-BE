# RAG STEP 111 — Collect usage metrics (RAG.metrics.collect.usage.metrics)

**Type:** process  
**Category:** metrics  
**Node ID:** `CollectMetrics`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CollectMetrics` (Collect usage metrics).

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
  `RAG STEP 111 (RAG.metrics.collect.usage.metrics): Collect usage metrics | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/metrics.py:135 — app.orchestrators.metrics.step_74__track_usage (score 0.31)
   Evidence: Score 0.31, RAG STEP 74 — UsageTracker.track Track API usage
ID: RAG.metrics.usagetracker.tr...
2) app/orchestrators/metrics.py:294 — app.orchestrators.metrics.step_111__collect_metrics (score 0.31)
   Evidence: Score 0.31, RAG STEP 111 — Collect usage metrics
ID: RAG.metrics.collect.usage.metrics
Type:...
3) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.30)
   Evidence: Score 0.30, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
4) app/services/usage_tracker.py:26 — app.services.usage_tracker.UsageMetrics (score 0.29)
   Evidence: Score 0.29, Container for usage metrics.
5) app/main.py:194 — app.main.metrics (score 0.28)
   Evidence: Score 0.28, Prometheus metrics endpoint for scraping.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->