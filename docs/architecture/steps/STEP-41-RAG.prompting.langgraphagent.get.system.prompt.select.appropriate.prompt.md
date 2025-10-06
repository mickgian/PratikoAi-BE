# RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt (RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt)

**Type:** process  
**Category:** prompting  
**Node ID:** `SelectPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SelectPrompt` (LangGraphAgent._get_system_prompt Select appropriate prompt).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/prompting.py:211` - `step_41__select_prompt()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator selecting appropriate system prompt using PromptTemplateManager. Routes to Step 42 (ClassConfidence) to check classification confidence for domain-specific prompts.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 41 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.32

Top candidates:
1) app/core/langgraph/graph.py:488 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.32)
   Evidence: Score 0.32, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
2) app/core/langgraph/graph.py:640 — app.core.langgraph.graph.LangGraphAgent._get_optimal_provider (score 0.32)
   Evidence: Score 0.32, Get the optimal LLM provider for the given messages.

Args:
    messages: List o...
3) app/core/langgraph/graph.py:504 — app.core.langgraph.graph.LangGraphAgent._get_classification_aware_routing (score 0.31)
   Evidence: Score 0.31, Return (routing_strategy, max_cost_eur) based solely on domain/action mapping.
-...
4) app/core/langgraph/graph.py:226 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.
5) app/orchestrators/prompting.py:203 — app.orchestrators.prompting._get_default_system_prompt (score 0.30)
   Evidence: Score 0.30, Get appropriate default system prompt based on query analysis.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Detected Node but not in runtime registry

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->