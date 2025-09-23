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
1) app/core/langgraph/graph.py:406 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.39)
   Evidence: Score 0.39, Select the appropriate system prompt (RAG STEPs 41/42/44) with full test-require...
2) app/core/langgraph/graph.py:579 — app.core.langgraph.graph.LangGraphAgent._prepare_messages_with_system_prompt (score 0.33)
   Evidence: Score 0.33, Ensure system message presence (RAG STEP 45 — CheckSysMsg) with backward-compati...
3) app/core/langgraph/graph.py:343 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.32)
   Evidence: Score 0.32, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
4) app/core/langgraph/graph.py:651 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.32)
   Evidence: Score 0.32, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...
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