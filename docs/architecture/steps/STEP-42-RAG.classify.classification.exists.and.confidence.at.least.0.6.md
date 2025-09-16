# RAG STEP 42 — Classification exists and confidence at least 0.6? (RAG.classify.classification.exists.and.confidence.at.least.0.6)

**Type:** decision  
**Category:** classify  
**Node ID:** `ClassConfidence`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ClassConfidence` (Classification exists and confidence at least 0.6?).

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
  `RAG STEP 42 (RAG.classify.classification.exists.and.confidence.at.least.0.6): Classification exists and confidence at least 0.6? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.42

Top candidates:
1) app/ragsteps/classify/step_42_rag_classify_classification_exists_and_confidence_at_least_0_6.py:1 — app.ragsteps.classify.step_42_rag_classify_classification_exists_and_confidence_at_least_0_6 (score 0.42)
   Evidence: Score 0.42, RAG STEP 42 — Classification exists and confidence at least 0.6?
ID: RAG.classif...
2) app/ragsteps/classify/step_42_rag_classify_classification_exists_and_confidence_at_least_0_6.py:30 — app.ragsteps.classify.step_42_rag_classify_classification_exists_and_confidence_at_least_0_6.run (score 0.41)
   Evidence: Score 0.41, Adapter shim for STEP 42 — ClassConfidence.
3) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.39)
   Evidence: Score 0.39, Calculate confidence scores for each domain
4) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.39)
   Evidence: Score 0.39, Calculate confidence scores for each action
5) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.37)
   Evidence: Score 0.37, Track domain-action classification usage and metrics.

Args:
    domain: The cla...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->