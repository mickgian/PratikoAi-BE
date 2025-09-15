# RAG STEP 75 — Response has tool_calls? (RAG.response.response.has.tool.calls)

**Type:** process  
**Category:** response  
**Node ID:** `ToolCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolCheck` (Response has tool_calls?).

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
  `RAG STEP 75 (RAG.response.response.has.tool.calls): Response has tool_calls? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/ragsteps/cache/step_59_rag_cache_langgraphagent_get_cached_llm_response_check_for_cached_response.py:40 — app.ragsteps.cache.step_59_rag_cache_langgraphagent_get_cached_llm_response_check_for_cached_response.run (score 0.26)
   Evidence: Score 0.26, Adapter for RAG STEP 59.

Expected behavior is defined in:
docs/architecture/ste...
2) app/api/v1/italian.py:65 — app.api.v1.italian.ComplianceCheckResponse (score 0.26)
   Evidence: Score 0.26, Compliance check response.
3) version-management/cli/version_cli.py:227 — version-management.cli.version_cli.VersionCLI.check_compatibility (score 0.26)
   Evidence: Score 0.26, Check compatibility for a version deployment.
4) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.26)
   Evidence: Score 0.26, Convert internal SearchResponse to API model.
5) app/core/decorators/cache.py:19 — app.core.decorators.cache.cache_llm_response (score 0.26)
   Evidence: Score 0.26, Decorator to cache LLM responses based on messages and model.

Args:
    ttl: Ti...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToolCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->