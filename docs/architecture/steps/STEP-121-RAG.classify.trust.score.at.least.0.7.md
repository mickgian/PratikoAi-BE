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
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/core/langgraph/graph.py:346 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.34)
   Evidence: Score 0.34, Get routing strategy and cost limit based on domain-action classification.

Args...
2) app/core/langgraph/graph.py:401 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.34)
   Evidence: Score 0.34, Get the appropriate system prompt based on classification.

Args:
    messages: ...
3) app/core/langgraph/graph.py:797 — app.core.langgraph.graph.LangGraphAgent._needs_complex_workflow (score 0.34)
   Evidence: Score 0.34, Determine if query needs tools/complex workflow based on classification.

Args:
...
4) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.34)
   Evidence: Score 0.34, Track domain-action classification usage and metrics.
    
    Args:
        dom...
5) app/services/ccnl_integration_service.py:163 — app.services.ccnl_integration_service.CCNLIntegrationService._extract_ccnl_parameters (score 0.28)
   Evidence: Score 0.28, Extract parameters for CCNL tool from user query and classification.

Args:
    ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->