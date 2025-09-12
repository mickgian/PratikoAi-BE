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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.30)
   Evidence: Score 0.30, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
2) app/core/langgraph/graph.py:63 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.
3) app/core/langgraph/graph.py:274 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.30)
   Evidence: Score 0.30, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
4) app/core/langgraph/graph.py:290 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.30)
   Evidence: Score 0.30, Get routing strategy and cost limit based on domain-action classification.

Args...
5) app/core/langgraph/graph.py:345 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.30)
   Evidence: Score 0.30, Get the appropriate system prompt based on classification.

Args:
    messages: ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ConvertMessages
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->