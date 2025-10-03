# RAG STEP 72 — Get FAILOVER provider (RAG.providers.get.failover.provider)

**Type:** process  
**Category:** providers  
**Node ID:** `FailoverProvider`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FailoverProvider` (Get FAILOVER provider).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/providers.py:1201` - `step_72__get_failover_provider()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator selecting failover provider when primary fails. Implements provider redundancy for high availability.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 72 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.51

Top candidates:
1) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.51)
   Evidence: Score 0.51, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
2) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.51)
   Evidence: Score 0.51, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...
3) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.50)
   Evidence: Score 0.50, Select optimal LLM provider based on domain-action requirements
4) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.47)
   Evidence: Score 0.47, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...
5) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.47)
   Evidence: Score 0.47, Main query router that integrates classification, prompt templates,
context enri...

Notes:
- Strong implementation match found
- Wired via graph registry ✅
- Incoming: [70], Outgoing: [64]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->