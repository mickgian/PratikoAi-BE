# RAG STEP 119 — ExpertFeedbackCollector.collect_feedback (RAG.metrics.expertfeedbackcollector.collect.feedback)

**Type:** process  
**Category:** metrics  
**Node ID:** `ExpertFeedbackCollector`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExpertFeedbackCollector` (ExpertFeedbackCollector.collect_feedback).

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
  `RAG STEP 119 (RAG.metrics.expertfeedbackcollector.collect.feedback): ExpertFeedbackCollector.collect_feedback | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.18

Top candidates:
1) app/services/failure_pattern_analyzer.py:273 — app.services.failure_pattern_analyzer.FailurePatternAnalyzer._categorize_feedback (score 0.18)
   Evidence: Score 0.18, Categorize feedback by Italian categories
2) rollback-system/health_monitor.py:163 — rollback-system.health_monitor.ApplicationHealthChecker.__init__ (score 0.17)
   Evidence: Score 0.17, method: __init__
3) rollback-system/health_monitor.py:318 — rollback-system.health_monitor.LogPreserver.__init__ (score 0.17)
   Evidence: Score 0.17, method: __init__
4) rollback-system/health_monitor.py:401 — rollback-system.health_monitor.HealthMonitor.__init__ (score 0.17)
   Evidence: Score 0.17, method: __init__
5) rollback-system/health_monitor.py:419 — rollback-system.health_monitor.HealthMonitor._load_config (score 0.17)
   Evidence: Score 0.17, Load configuration from file.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ExpertFeedbackCollector
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->