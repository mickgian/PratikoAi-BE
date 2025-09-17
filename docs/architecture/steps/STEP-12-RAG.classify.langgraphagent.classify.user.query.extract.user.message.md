# RAG STEP 12 — LangGraphAgent._classify_user_query Extract user message (RAG.classify.langgraphagent.classify.user.query.extract.user.message)

**Type:** process  
**Category:** classify  
**Node ID:** `ExtractQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractQuery` (LangGraphAgent._classify_user_query Extract user message).

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
  `RAG STEP 12 (RAG.classify.langgraphagent.classify.user.query.extract.user.message): LangGraphAgent._classify_user_query Extract user message | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.40

Top candidates:
1) app/core/langgraph/graph.py:1052 — app.core.langgraph.graph.LangGraphAgent._needs_complex_workflow (score 0.40)
   Evidence: Score 0.40, Determine if query needs tools/complex workflow based on classification.

Args:
...
2) app/core/langgraph/graph.py:359 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.40)
   Evidence: Score 0.40, Get routing strategy and cost limit based on domain-action classification.

Args...
3) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.39)
   Evidence: Score 0.39, Calculate confidence scores for each domain
4) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.39)
   Evidence: Score 0.39, Calculate confidence scores for each action
5) app/services/ccnl_integration_service.py:163 — app.services.ccnl_integration_service.CCNLIntegrationService._extract_ccnl_parameters (score 0.37)
   Evidence: Score 0.37, Extract parameters for CCNL tool from user query and classification.

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