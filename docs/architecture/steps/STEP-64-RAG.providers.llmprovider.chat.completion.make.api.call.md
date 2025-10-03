# RAG STEP 64 — LLMProvider.chat_completion Make API call (RAG.providers.llmprovider.chat.completion.make.api.call)

**Type:** process  
**Category:** providers  
**Node ID:** `LLMCall`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `LLMCall` (LLMProvider.chat_completion Make API call).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/providers.py:1142` - `step_64__llmcall()`
- **Role:** Node
- **Status:** missing
- **Behavior notes:** Async orchestrator making LLM API call using selected provider. Handles retries, error handling, and response processing. Routes to Step 67 (LLMSuccess) to check call result.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing provider infrastructure

## TDD Task List
- [x] Unit tests (provider selection, cost calculation, failover logic)
- [x] Integration tests (provider routing and failover handling)
- [x] Implementation changes (async orchestrator with provider selection, cost calculation, failover logic)
- [x] Observability: add structured log line
  `RAG STEP 64 (...): ... | attrs={provider_name, cost_estimate, routing_strategy}`
- [x] Feature flag / config if needed (provider settings and cost thresholds)
- [x] Rollout plan (implemented with provider reliability and cost optimization safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.48

Top candidates:
1) app/core/llm/factory.py:298 — app.core.llm.factory.LLMFactory._route_failover (score 0.48)
   Evidence: Score 0.48, Route with failover logic - primary provider with fallbacks.

Args:
    provider...
2) app/services/enhanced_query_router.py:213 — app.services.enhanced_query_router.EnhancedQueryRouter._select_llm_provider (score 0.47)
   Evidence: Score 0.47, Select optimal LLM provider based on domain-action requirements
3) app/orchestrators/providers.py:1201 — app.orchestrators.providers.step_72__get_failover_provider (score 0.46)
   Evidence: Score 0.46, RAG STEP 72 — Get FAILOVER provider
ID: RAG.providers.get.failover.provider
Type...
4) app/services/enhanced_query_router.py:46 — app.services.enhanced_query_router.EnhancedQueryRouter (score 0.46)
   Evidence: Score 0.46, Main query router that integrates classification, prompt templates,
context enri...
5) app/core/langgraph/nodes/step_072__failover_provider.py:9 — app.core.langgraph.nodes.step_072__failover_provider.node_step_72 (score 0.45)
   Evidence: Score 0.45, Node wrapper for Step 72: Get failover provider.

Notes:
- Strong implementation match found
- Low confidence in symbol matching
- Wired via graph registry ✅
- Incoming: [62, 72, 73], Outgoing: [67]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
- Test failover and retry mechanisms
<!-- AUTO-AUDIT:END -->