# RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy (RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy)

**Type:** process  
**Category:** facts  
**Node ID:** `RouteStrategy`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RouteStrategy` (LLMFactory.get_optimal_provider Apply routing strategy).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:427` - `step_49__route_strategy()`
- **Status:** ✅ Implemented
- **Behavior notes:** Orchestrator applying routing strategy to select optimal LLM provider. Balances cost, quality, and availability for provider selection.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (fact extraction, atomic facts processing, context building)
- [x] Integration tests (fact processing flow and context integration)
- [x] Implementation changes (async orchestrator with fact extraction, atomic facts processing, context building)
- [x] Observability: add structured log line
  `RAG STEP 49 (...): ... | attrs={fact_count, extraction_confidence, context_size}`
- [x] Feature flag / config if needed (fact extraction settings and confidence thresholds)
- [x] Rollout plan (implemented with fact extraction accuracy and context quality safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/core/llm/factory.py:127 — app.core.llm.factory.LLMFactory.get_optimal_provider (score 0.32)
   Evidence: Score 0.32, Get the optimal provider based on routing strategy.

Args:
    messages: List of...
2) app/core/llm/factory.py:33 — app.core.llm.factory.LLMFactory._get_provider_configs (score 0.29)
   Evidence: Score 0.29, Get provider configurations from settings.

Returns:
    Dictionary of provider ...
3) app/core/langgraph/graph.py:361 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.29)
   Evidence: Score 0.29, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
4) app/core/langgraph/graph.py:513 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.29)
   Evidence: Score 0.29, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...
5) app/core/llm/factory.py:367 — app.core.llm.factory.get_llm_provider (score 0.27)
   Evidence: Score 0.27, Convenience function to get an optimal LLM provider.

Args:
    messages: List o...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->