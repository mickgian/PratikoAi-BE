# RAG STEP 38 — Use rule-based classification (RAG.platform.use.rule.based.classification)

**Type:** process  
**Category:** platform  
**Node ID:** `UseRuleBased`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `UseRuleBased` (Use rule-based classification).

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
  `RAG STEP 38 (RAG.platform.use.rule.based.classification): Use rule-based classification | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.26)
   Evidence: Score 0.26, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
2) app/services/document_uploader.py:277 — app.services.document_uploader.DocumentUploader._signature_based_scan (score 0.26)
   Evidence: Score 0.26, Signature-based malware detection
3) rollback-system/health_monitor.py:645 — rollback-system.health_monitor.HealthMonitor._evaluate_rule_condition (score 0.26)
   Evidence: Score 0.26, Evaluate a monitoring rule condition.
4) app/core/llm/cost_calculator.py:281 — app.core.llm.cost_calculator.CostCalculator.should_use_cache (score 0.25)
   Evidence: Score 0.25, Determine if caching would be beneficial for this query.

Args:
    cost_estimat...
5) app/services/domain_action_classifier.py:633 — app.services.domain_action_classifier.DomainActionClassifier.get_classification_stats (score 0.25)
   Evidence: Score 0.25, Get statistics about the classification patterns

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for UseRuleBased
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->