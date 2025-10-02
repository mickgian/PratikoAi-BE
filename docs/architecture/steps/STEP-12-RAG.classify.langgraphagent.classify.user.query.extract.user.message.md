# RAG STEP 12 — LangGraphAgent._classify_user_query Extract user message (RAG.classify.langgraphagent.classify.user.query.extract.user.message)

**Type:** process  
**Category:** classify  
**Node ID:** `ExtractQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractQuery` (LangGraphAgent._classify_user_query Extract user message).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/classify.py:16` - `step_12__extract_query()`
- **Role:** Internal
- **Status:** missing
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 12 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.46

Top candidates:
1) app/core/langgraph/graph.py:377 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.46)
   Evidence: Score 0.46, Return (routing_strategy, max_cost_eur) based solely on domain/action mapping.
-...
2) app/orchestrators/classify.py:210 — app.orchestrators.classify.step_31__classify_domain (score 0.46)
   Evidence: Score 0.46, RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
ID: RAG....
3) app/orchestrators/classify.py:544 — app.orchestrators.classify.step_35__llmfallback (score 0.43)
   Evidence: Score 0.43, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
4) app/orchestrators/classify.py:317 — app.orchestrators.classify.step_32__calc_scores (score 0.43)
   Evidence: Score 0.43, RAG STEP 32 — Calculate domain and action scores Match Italian keywords
ID: RAG....
5) app/orchestrators/classify.py:677 — app.orchestrators.classify.step_35__llm_fallback (score 0.43)
   Evidence: Score 0.43, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Internal step is correctly implemented (no wiring required)

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->