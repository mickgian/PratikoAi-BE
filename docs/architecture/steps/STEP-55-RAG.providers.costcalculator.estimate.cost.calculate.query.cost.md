# RAG STEP 55 — CostCalculator.estimate_cost Calculate query cost (RAG.providers.costcalculator.estimate.cost.calculate.query.cost)

**Type:** process  
**Category:** providers  
**Node ID:** `EstimateCost`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `EstimateCost` (CostCalculator.estimate_cost Calculate query cost).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/providers.py:635` - `step_55__estimate_cost()`
- **Role:** Node
- **Status:** missing
- **Behavior notes:** Orchestrator calculating estimated query costs for LLM providers. Analyzes token counts, provider pricing, and query complexity to provide cost estimates before execution.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 55 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.50

Top candidates:
1) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.50)
   Evidence: Score 0.50, Select optimal LLM provider based on domain-action requirements
2) app/core/llm/cost_calculator.py:141 — app.core.llm.cost_calculator.CostCalculator.calculate_cost_estimate (score 0.49)
   Evidence: Score 0.49, Calculate cost estimate for a query with a specific provider.

Args:
    provide...
3) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.48)
   Evidence: Score 0.48, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
4) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.48)
   Evidence: Score 0.48, Main query router that integrates classification, prompt templates,
context enri...
5) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.46)
   Evidence: Score 0.46, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->