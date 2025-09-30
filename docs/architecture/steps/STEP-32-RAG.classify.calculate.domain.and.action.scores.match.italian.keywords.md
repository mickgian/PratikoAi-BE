# RAG STEP 32 — Calculate domain and action scores Match Italian keywords (RAG.classify.calculate.domain.and.action.scores.match.italian.keywords)

**Type:** process  
**Category:** classify  
**Node ID:** `CalcScores`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CalcScores` (Calculate domain and action scores Match Italian keywords).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/classify.py:317` - `step_32__calc_scores()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator calculating domain and action scores by matching Italian keywords from canonicalized facts. Uses scoring algorithms to determine classification confidence. Routes to Step 33 (ConfidenceCheck) for threshold validation.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 32 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.48

Top candidates:
1) app/orchestrators/classify.py:317 — app.orchestrators.classify.step_32__calc_scores (score 0.48)
   Evidence: Score 0.48, RAG STEP 32 — Calculate domain and action scores Match Italian keywords
ID: RAG....
2) app/orchestrators/classify.py:210 — app.orchestrators.classify.step_31__classify_domain (score 0.46)
   Evidence: Score 0.46, RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
ID: RAG....
3) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.43)
   Evidence: Score 0.43, Calculate confidence scores for each domain
4) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.43)
   Evidence: Score 0.43, Calculate confidence scores for each action
5) app/orchestrators/classify.py:544 — app.orchestrators.classify.step_35__llmfallback (score 0.43)
   Evidence: Score 0.43, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->