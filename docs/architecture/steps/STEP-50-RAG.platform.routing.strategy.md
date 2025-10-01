# RAG STEP 50 — Routing strategy? (RAG.platform.routing.strategy)

**Type:** decision  
**Category:** platform  
**Node ID:** `StrategyType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StrategyType` (Routing strategy?).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** missing
- **Paths / classes:** `app/orchestrators/platform.py:1203` - `step_50__strategy_type()`
- **Behavior notes:** Runtime boundary; determines routing strategy type; routes to cheapest, best, balanced, or primary provider selection.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 50 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/platform.py:1203 — app.orchestrators.platform.step_50__strategy_type (score 0.31)
   Evidence: Score 0.31, RAG STEP 50 — Routing strategy?
ID: RAG.platform.routing.strategy
Type: decision...
2) app/orchestrators/routing.py:14 — app.orchestrators.routing.step_79__tool_type (score 0.31)
   Evidence: Score 0.31, RAG STEP 79 — Tool type?

ID: RAG.routing.tool.type
Type: decision | Category: r...
3) app/orchestrators/routing.py:94 — app.orchestrators.routing._determine_tool_type_and_routing (score 0.30)
   Evidence: Score 0.30, Determine tool type and routing destination based on tool call context.

Maps to...
4) app/orchestrators/routing.py:271 — app.orchestrators.routing._handle_tool_type_error (score 0.30)
   Evidence: Score 0.30, Handle errors in tool type detection with graceful fallback.
5) app/core/langgraph/graph.py:361 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.28)
   Evidence: Score 0.28, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->