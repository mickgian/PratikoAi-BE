# RAG STEP 48 — LangGraphAgent._get_optimal_provider Select LLM provider (RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `SelectProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SelectProvider` (LangGraphAgent._get_optimal_provider Select LLM provider).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ✅ Implemented
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
  `RAG STEP 48 (RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider): LangGraphAgent._get_optimal_provider Select LLM provider | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.50

Top candidates:
1) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.50)
   Evidence: Score 0.50, Select optimal LLM provider based on domain-action requirements
2) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.48)
   Evidence: Score 0.48, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
3) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.48)
   Evidence: Score 0.48, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...
4) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.46)
   Evidence: Score 0.46, Main query router that integrates classification, prompt templates,
context enri...
5) app/core/langgraph/graph.py:495 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.45)
   Evidence: Score 0.45, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->