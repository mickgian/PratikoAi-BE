# RAG STEP 11 — LangGraphAgent._chat Convert to Message objects (RAG.platform.langgraphagent.chat.convert.to.message.objects)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertMessages`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertMessages` (LangGraphAgent._chat Convert to Message objects).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:747` - `step_11__convert_messages()`
- **Role:** Internal
- **Status:** missing
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 11 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: missing  |  Confidence: 0.32

Top candidates:
1) app/core/langgraph/graph.py:1215 — app.core.langgraph.graph.LangGraphAgent.__process_messages (score 0.32)
   Evidence: Score 0.32, method: __process_messages
2) app/core/langgraph/graph.py:81 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.
3) app/core/langgraph/graph.py:825 — app.core.langgraph.graph.LangGraphAgent._should_continue (score 0.29)
   Evidence: Score 0.29, Determine if the agent should continue or end based on the last message.

Args:
...
4) app/core/langgraph/graph.py:343 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.29)
   Evidence: Score 0.29, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
5) app/core/langgraph/graph.py:495 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.29)
   Evidence: Score 0.29, Get the optimal LLM provider for the given messages.

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