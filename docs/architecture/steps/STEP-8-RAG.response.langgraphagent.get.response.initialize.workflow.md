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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/core/langgraph/graph.py:63 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.
2) app/core/langgraph/graph.py:274 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.30)
   Evidence: Score 0.30, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
3) app/core/langgraph/graph.py:290 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.30)
   Evidence: Score 0.30, Get routing strategy and cost limit based on domain-action classification.

Args...
4) app/core/langgraph/graph.py:345 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.30)
   Evidence: Score 0.30, Get the appropriate system prompt based on classification.

Args:
    messages: ...
5) app/core/langgraph/graph.py:407 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.30)
   Evidence: Score 0.30, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for InitAgent
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->