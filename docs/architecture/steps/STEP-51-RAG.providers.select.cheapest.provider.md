# RAG STEP 51 — Select cheapest provider (RAG.providers.select.cheapest.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `CheapProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CheapProvider` (Select cheapest provider).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/providers.py:128` - `step_51__cheap_provider()`
- **Status:** ✅ Implemented
- **Behavior notes:** Orchestrator selecting the cheapest available LLM provider based on cost analysis. Optimizes for minimal API costs while maintaining acceptable quality thresholds.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 51 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

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
3) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.47)
   Evidence: Score 0.47, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...
4) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.46)
   Evidence: Score 0.46, Main query router that integrates classification, prompt templates,
context enri...
5) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.42)
   Evidence: Score 0.42, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->