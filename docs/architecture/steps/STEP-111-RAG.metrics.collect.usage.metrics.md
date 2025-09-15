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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.30)
   Evidence: Score 0.30, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
2) app/services/usage_tracker.py:26 — app.services.usage_tracker.UsageMetrics (score 0.29)
   Evidence: Score 0.29, Container for usage metrics.
3) app/core/metrics.py:39 — app.core.metrics.setup_metrics (score 0.27)
   Evidence: Score 0.27, Set up Prometheus metrics middleware and endpoints.

Args:
    app: FastAPI appl...
4) app/core/monitoring/metrics.py:310 — app.core.monitoring.metrics.initialize_metrics (score 0.27)
   Evidence: Score 0.27, Initialize metrics with system information and default values.
5) app/services/metrics_service.py:72 — app.services.metrics_service.MetricsService.__init__ (score 0.27)
   Evidence: Score 0.27, method: __init__

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for CollectMetrics
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->