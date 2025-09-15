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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/core/metrics.py:39 — app.core.metrics.setup_metrics (score 0.27)
   Evidence: Score 0.27, Set up Prometheus metrics middleware and endpoints.

    Args:
        app: Fast...
2) app/core/monitoring/metrics.py:310 — app.core.monitoring.metrics.initialize_metrics (score 0.26)
   Evidence: Score 0.26, Initialize metrics with system information and default values.
3) app/core/monitoring/metrics.py:353 — app.core.monitoring.metrics.update_system_metrics (score 0.26)
   Evidence: Score 0.26, Update system-level metrics like memory and CPU usage.
4) app/core/monitoring/metrics.py:376 — app.core.monitoring.metrics.get_registry (score 0.26)
   Evidence: Score 0.26, Get the Prometheus registry for metrics export.
5) app/core/monitoring/metrics.py:381 — app.core.monitoring.metrics.get_metrics_content (score 0.26)
   Evidence: Score 0.26, Get metrics in Prometheus format.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for CollectMetrics
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->