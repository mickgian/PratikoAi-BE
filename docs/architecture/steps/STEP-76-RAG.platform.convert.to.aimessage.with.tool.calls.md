# RAG STEP 76 — Convert to AIMessage with tool_calls (RAG.platform.convert.to.aimessage.with.tool.calls)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertAIMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertAIMsg` (Convert to AIMessage with tool_calls).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:1784` - `step_76__convert_aimsg()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator converting responses to AIMessage format with tool calls. Handles LLM responses with tool invocations for multi-step interactions.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 76 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/orchestrators/platform.py:1784 — app.orchestrators.platform.step_76__convert_aimsg (score 0.28)
   Evidence: Score 0.28, RAG STEP 76 — Convert to AIMessage with tool_calls
ID: RAG.platform.convert.to.a...
2) app/orchestrators/kb.py:150 — app.orchestrators.kb.step_80__kbquery_tool (score 0.26)
   Evidence: Score 0.26, RAG STEP 80 — KnowledgeSearchTool.search KB on demand.

ID: RAG.kb.knowledgesear...
3) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.25)
   Evidence: Score 0.25, Convert internal SearchResponse to API model.
4) app/orchestrators/cache.py:909 — app.orchestrators.cache._cache_feedback_with_ttl (score 0.25)
   Evidence: Score 0.25, Helper function to cache expert feedback with 1-hour TTL.
Handles cache operatio...
5) app/orchestrators/facts.py:675 — app.orchestrators.facts.step_98__to_tool_results (score 0.25)
   Evidence: Score 0.25, RAG STEP 98 — Convert to ToolMessage facts and spans
ID: RAG.facts.convert.to.to...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ConvertAIMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->