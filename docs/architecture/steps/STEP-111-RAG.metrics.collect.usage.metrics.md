# RAG STEP 111 — Collect usage metrics (RAG.metrics.collect.usage.metrics)

**Type:** process  
**Category:** metrics  
**Node ID:** `CollectMetrics`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CollectMetrics` (Collect usage metrics).

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_111__collect_metrics.py` - `node_step_111`, `app/orchestrators/metrics.py:297` - `step_111__collect_metrics()`
- **Role:** Node
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator collecting usage metrics for analytics and monitoring. Tracks request counts, response times, and resource utilization.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing metrics tracking infrastructure

## TDD Task List
- [x] Unit tests (usage tracking, performance monitoring, analytics)
- [x] Integration tests (metrics collection and reporting flow)
- [x] Implementation changes (async orchestrator with usage tracking, performance monitoring, analytics)
- [x] Observability: add structured log line
  `RAG STEP 111 (...): ... | attrs={metric_type, value, timestamp}`
- [x] Feature flag / config if needed (metrics collection settings and retention policies)
- [x] Rollout plan (implemented with metrics accuracy and storage efficiency safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/metrics.py:139 — app.orchestrators.metrics.step_74__track_usage (score 0.31)
   Evidence: Score 0.31, RAG STEP 74 — UsageTracker.track Track API usage
ID: RAG.metrics.usagetracker.tr...
2) app/orchestrators/metrics.py:297 — app.orchestrators.metrics.step_111__collect_metrics (score 0.31)
   Evidence: Score 0.31, RAG STEP 111 — Collect usage metrics
ID: RAG.metrics.collect.usage.metrics
Type:...
3) app/orchestrators/metrics.py:448 — app.orchestrators.metrics._collect_expert_feedback (score 0.31)
   Evidence: Score 0.31, Helper function to collect expert feedback using ExpertFeedbackCollector service...
4) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.30)
   Evidence: Score 0.30, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
5) app/services/usage_tracker.py:26 — app.services.usage_tracker.UsageMetrics (score 0.29)
   Evidence: Score 0.29, Container for usage metrics.

Notes:
- Strong implementation match found
- Low confidence in symbol matching
- Wired via graph registry ✅
- Incoming: [104, 110], Outgoing: [112]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->