# RAG STEP 56 — Cost within budget? (RAG.providers.cost.within.budget)

**Type:** decision  
**Category:** providers  
**Node ID:** `CostCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CostCheck` (Cost within budget?).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/providers.py:739` - `step_56__cost_check()`
- **Status:** ✅ Implemented
- **Behavior notes:** Orchestrator checking if estimated cost is within budget constraints. Decision point for provider selection based on cost limits.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 56 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.49

Top candidates:
1) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.49)
   Evidence: Score 0.49, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
2) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.48)
   Evidence: Score 0.48, Select optimal LLM provider based on domain-action requirements
3) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.46)
   Evidence: Score 0.46, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...
4) app/core/langgraph/nodes/step_072__failover_provider.py:9 — app.core.langgraph.nodes.step_072__failover_provider.node_step_72 (score 0.45)
   Evidence: Score 0.45, Node wrapper for Step 72: Get failover provider.
5) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.44)
   Evidence: Score 0.44, Main query router that integrates classification, prompt templates,
context enri...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Detected Node but not in runtime registry

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->