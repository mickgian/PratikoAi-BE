# RAG STEP 8 — LangGraphAgent.get_response Initialize workflow (RAG.response.langgraphagent.get.response.initialize.workflow)

**Type:** process  
**Category:** response  
**Node ID:** `InitAgent`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `InitAgent` (LangGraphAgent.get_response Initialize workflow).

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
  `RAG STEP 8 (RAG.response.langgraphagent.get.response.initialize.workflow): LangGraphAgent.get_response Initialize workflow | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.33

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