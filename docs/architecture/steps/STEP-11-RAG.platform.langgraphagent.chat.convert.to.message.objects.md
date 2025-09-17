# RAG STEP 11 — LangGraphAgent._chat Convert to Message objects (RAG.platform.langgraphagent.chat.convert.to.message.objects)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertMessages`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertMessages` (LangGraphAgent._chat Convert to Message objects).

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
  `RAG STEP 11 (RAG.platform.langgraphagent.chat.convert.to.message.objects): LangGraphAgent._chat Convert to Message objects | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/core/langgraph/graph.py:1326 — app.core.langgraph.graph.LangGraphAgent.__process_messages (score 0.32)
   Evidence: Score 0.32, method: __process_messages
2) app/core/langgraph/graph.py:607 — app.core.langgraph.graph.LangGraphAgent._prepare_messages_with_system_prompt (score 0.30)
   Evidence: Score 0.30, Ensure system message presence (RAG STEP 45 — CheckSysMsg) with backward-compati...
3) app/core/langgraph/graph.py:81 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.
4) app/core/langgraph/graph.py:936 — app.core.langgraph.graph.LangGraphAgent._should_continue (score 0.29)
   Evidence: Score 0.29, Determine if the agent should continue or end based on the last message.

Args:
...
5) app/core/langgraph/graph.py:343 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.29)
   Evidence: Score 0.29, Get the LLM routing strategy from configuration.

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