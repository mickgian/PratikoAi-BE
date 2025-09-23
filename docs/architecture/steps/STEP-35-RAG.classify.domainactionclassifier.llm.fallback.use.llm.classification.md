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
Status: 🔌  |  Confidence: 0.46

Top candidates:
1) app/orchestrators/classify.py:542 — app.orchestrators.classify.step_35__llmfallback (score 0.46)
   Evidence: Score 0.46, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
2) app/core/langgraph/graph.py:359 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.43)
   Evidence: Score 0.43, Return (routing_strategy, max_cost_eur) based solely on domain/action mapping.
-...
3) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.41)
   Evidence: Score 0.41, Calculate confidence scores for each domain
4) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.41)
   Evidence: Score 0.41, Calculate confidence scores for each action
5) app/orchestrators/classify.py:829 — app.orchestrators.classify.step_43__domain_prompt (score 0.39)
   Evidence: Score 0.39, RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt
ID: RA...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->