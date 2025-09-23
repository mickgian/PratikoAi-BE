# RAG STEP 58 — Select cheaper provider or fail (RAG.providers.select.cheaper.provider.or.fail)

**Type:** process  
**Category:** providers  
**Node ID:** `CheaperProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CheaperProvider` (Select cheaper provider or fail).

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
  `RAG STEP 58 (RAG.providers.select.cheaper.provider.or.fail): Select cheaper provider or fail | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.52

Top candidates:
1) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.52)
   Evidence: Score 0.52, Select optimal LLM provider based on domain-action requirements
2) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.50)
   Evidence: Score 0.50, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
3) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.46)
   Evidence: Score 0.46, Main query router that integrates classification, prompt templates,
context enri...
4) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.42)
   Evidence: Score 0.42, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...
5) app/orchestrators/providers.py:14 — app.orchestrators.providers.step_48__select_provider (score 0.42)
   Evidence: Score 0.42, RAG STEP 48 — LangGraphAgent._get_optimal_provider Select LLM provider
ID: RAG.p...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->