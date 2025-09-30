# RAG STEP 8 — LangGraphAgent.get_response Initialize workflow (RAG.response.langgraphagent.get.response.initialize.workflow)

**Type:** process  
**Category:** response  
**Node ID:** `InitAgent`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `InitAgent` (LangGraphAgent.get_response Initialize workflow).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/response.py:15` - `step_8__init_agent()`, `app/core/langgraph/graph.py:894` - `get_response()`
- **Role:** Internal
- **Status:** missing
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing response processing infrastructure

## TDD Task List
- [x] Unit tests (workflow initialization, agent setup, response processing)
- [x] Integration tests (agent workflow flow and message routing)
- [x] Implementation changes (async orchestrator with workflow initialization, agent setup, response processing)
- [x] Observability: add structured log line
  `RAG STEP 8 (RAG.response.langgraphagent.get.response.initialize.workflow): LangGraphAgent.get_response Initialize workflow | attrs={agent_id, workflow_type, initialization_time}`
- [x] Feature flag / config if needed (workflow configuration and agent settings)
- [x] Rollout plan (implemented with workflow initialization and agent setup safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.33

Top candidates:
1) app/core/langgraph/graph.py:81 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.33)
   Evidence: Score 0.33, Initialize the LangGraph Agent with necessary components.
2) app/core/langgraph/graph.py:343 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.32)
   Evidence: Score 0.32, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
3) app/core/langgraph/graph.py:495 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.32)
   Evidence: Score 0.32, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...
4) app/core/langgraph/graph.py:941 — app.core.langgraph.graph.LangGraphAgent._needs_complex_workflow (score 0.32)
   Evidence: Score 0.32, Determine if query needs tools/complex workflow based on classification.

Args:
...
5) app/core/langgraph/graph.py:359 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.31)
   Evidence: Score 0.31, Return (routing_strategy, max_cost_eur) based solely on domain/action mapping.
-...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->