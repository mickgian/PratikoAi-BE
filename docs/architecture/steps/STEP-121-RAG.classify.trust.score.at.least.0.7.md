# RAG STEP 121 — Trust score at least 0.7? (RAG.classify.trust.score.at.least.0.7)

**Type:** decision  
**Category:** classify  
**Node ID:** `TrustScoreOK`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `TrustScoreOK` (Trust score at least 0.7?).

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
  `RAG STEP 121 (RAG.classify.trust.score.at.least.0.7): Trust score at least 0.7? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.38

Top candidates:
1) app/core/langgraph/graph.py:290 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.38)
   Evidence: Score 0.38, Get routing strategy and cost limit based on domain-action classification.

Args...
2) app/core/langgraph/graph.py:345 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.38)
   Evidence: Score 0.38, Get the appropriate system prompt based on classification.

Args:
    messages: ...
3) app/core/langgraph/graph.py:741 — app.core.langgraph.graph.LangGraphAgent._needs_complex_workflow (score 0.38)
   Evidence: Score 0.38, Determine if query needs tools/complex workflow based on classification.

Args:
...
4) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.38)
   Evidence: Score 0.38, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
5) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.33)
   Evidence: Score 0.33, Calculate confidence scores for each domain

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->