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
Status: 🔌  |  Confidence: 0.35

Top candidates:
1) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.35)
   Evidence: Score 0.35, Calculate confidence scores for each domain
2) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.35)
   Evidence: Score 0.35, Calculate confidence scores for each action
3) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.32)
   Evidence: Score 0.32, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
4) app/services/domain_action_classifier.py:26 — app.services.domain_action_classifier.Domain (score 0.32)
   Evidence: Score 0.32, Professional domains for Italian market
5) app/services/domain_action_classifier.py:35 — app.services.domain_action_classifier.Action (score 0.32)
   Evidence: Score 0.32, Professional actions/intents

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->