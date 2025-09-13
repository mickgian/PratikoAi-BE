# RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification (RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification)

**Type:** process  
**Category:** classify  
**Node ID:** `LLMFallback`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `LLMFallback` (DomainActionClassifier._llm_fallback Use LLM classification).

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
  `RAG STEP 35 (RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification): DomainActionClassifier._llm_fallback Use LLM classification | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.41

Top candidates:
1) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.41)
   Evidence: Score 0.41, Calculate confidence scores for each domain
2) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.41)
   Evidence: Score 0.41, Calculate confidence scores for each action
3) app/services/domain_action_classifier.py:516 — app.services.domain_action_classifier.DomainActionClassifier._extract_sub_domain (score 0.36)
   Evidence: Score 0.36, Extract sub-domain from query based on domain patterns
4) app/services/domain_action_classifier.py:530 — app.services.domain_action_classifier.DomainActionClassifier._extract_document_type (score 0.36)
   Evidence: Score 0.36, Extract document type for document generation actions
5) app/core/llm/cost_calculator.py:51 — app.core.llm.cost_calculator.CostCalculator.classify_query_complexity (score 0.36)
   Evidence: Score 0.36, Classify the complexity of a query based on content analysis.

Args:
    message...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->