# RAG STEP 33 — Confidence at least threshold? (RAG.classify.confidence.at.least.threshold)

**Type:** process  
**Category:** classify  
**Node ID:** `ConfidenceCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConfidenceCheck` (Confidence at least threshold?).

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
  `RAG STEP 33 (RAG.classify.confidence.at.least.threshold): Confidence at least threshold? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/services/domain_action_classifier.py:26 — app.services.domain_action_classifier.Domain (score 0.32)
   Evidence: Score 0.32, Professional domains for Italian market
2) app/services/domain_action_classifier.py:35 — app.services.domain_action_classifier.Action (score 0.32)
   Evidence: Score 0.32, Professional actions/intents
3) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.31)
   Evidence: Score 0.31, Calculate confidence scores for each domain
4) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.31)
   Evidence: Score 0.31, Calculate confidence scores for each action
5) app/core/langgraph/graph.py:290 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.31)
   Evidence: Score 0.31, Get routing strategy and cost limit based on domain-action classification.

Args...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->