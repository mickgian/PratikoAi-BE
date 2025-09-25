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
Status: 🔌  |  Confidence: 0.46

Top candidates:
1) app/core/langgraph/graph.py:359 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.46)
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

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->