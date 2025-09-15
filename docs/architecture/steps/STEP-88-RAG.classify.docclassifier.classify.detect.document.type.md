# RAG STEP 88 — DocClassifier.classify Detect document type (RAG.classify.docclassifier.classify.detect.document.type)

**Type:** process  
**Category:** classify  
**Node ID:** `DocClassify`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocClassify` (DocClassifier.classify Detect document type).

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
  `RAG STEP 88 (RAG.classify.docclassifier.classify.detect.document.type): DocClassifier.classify Detect document type | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.29)
   Evidence: Score 0.29, Track domain-action classification usage and metrics.
    
    Args:
        dom...
2) app/core/langgraph/graph.py:346 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.28)
   Evidence: Score 0.28, Get routing strategy and cost limit based on domain-action classification.

Args...
3) app/core/langgraph/graph.py:401 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.28)
   Evidence: Score 0.28, Get the appropriate system prompt based on classification.

Args:
    messages: ...
4) app/core/langgraph/graph.py:797 — app.core.langgraph.graph.LangGraphAgent._needs_complex_workflow (score 0.28)
   Evidence: Score 0.28, Determine if query needs tools/complex workflow based on classification.

Args:
...
5) app/services/ccnl_integration_service.py:163 — app.services.ccnl_integration_service.CCNLIntegrationService._extract_ccnl_parameters (score 0.28)
   Evidence: Score 0.28, Extract parameters for CCNL tool from user query and classification.

Args:
    ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DocClassify
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->