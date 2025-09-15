# RAG STEP 102 — LangGraphAgent.__process_messages Convert to dict (RAG.response.langgraphagent.process.messages.convert.to.dict)

**Type:** process  
**Category:** response  
**Node ID:** `ProcessMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ProcessMsg` (LangGraphAgent.__process_messages Convert to dict).

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
  `RAG STEP 102 (RAG.response.langgraphagent.process.messages.convert.to.dict): LangGraphAgent.__process_messages Convert to dict | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/core/langgraph/graph.py:1077 — app.core.langgraph.graph.LangGraphAgent.__process_messages (score 0.29)
   Evidence: Score 0.29, method: __process_messages
2) app/core/langgraph/graph.py:64 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.26)
   Evidence: Score 0.26, Initialize the LangGraph Agent with necessary components.
3) app/core/langgraph/graph.py:330 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.26)
   Evidence: Score 0.26, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
4) app/core/langgraph/graph.py:346 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.26)
   Evidence: Score 0.26, Get routing strategy and cost limit based on domain-action classification.

Args...
5) app/core/langgraph/graph.py:401 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.26)
   Evidence: Score 0.26, Get the appropriate system prompt based on classification.

Args:
    messages: ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ProcessMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->