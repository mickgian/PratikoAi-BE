# RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt (RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt)

**Type:** process  
**Category:** prompting  
**Node ID:** `SelectPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SelectPrompt` (LangGraphAgent._get_system_prompt Select appropriate prompt).

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
  `RAG STEP 41 (RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt): LangGraphAgent._get_system_prompt Select appropriate prompt | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.39

Top candidates:
1) app/core/langgraph/graph.py:529 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.39)
   Evidence: Score 0.39, Get the appropriate system prompt based on classification.

Args:
    messages: ...
2) app/core/langgraph/graph.py:458 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.32)
   Evidence: Score 0.32, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
3) app/core/langgraph/graph.py:591 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.32)
   Evidence: Score 0.32, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...
4) app/core/langgraph/graph.py:474 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.31)
   Evidence: Score 0.31, Get routing strategy and cost limit based on domain-action classification.

Args...
5) app/core/langgraph/graph.py:61 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->