# RAG STEP 99 — Return to tool caller (RAG.platform.return.to.tool.caller)

**Type:** process  
**Category:** platform  
**Node ID:** `ToolResults`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolResults` (Return to tool caller).

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
  `RAG STEP 99 (RAG.platform.return.to.tool.caller): Return to tool caller | attrs={...}`
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
1) evals/helpers.py:129 — evals.helpers.process_trace_results (score 0.26)
   Evidence: Score 0.26, Process results for a single trace.

Args:
    report: The report dictionary.
  ...
2) app/ragsteps/routing/step_79_rag_routing_tool_type.py:64 — app.ragsteps.routing.step_79_rag_routing_tool_type.step_79_rag_routing_tool_type (score 0.26)
   Evidence: Score 0.26, Canonical symbol for auditor: STEP 79 — Tool type? (RAG.routing.tool.type)

Dele...
3) app/services/hybrid_search_engine.py:406 — app.services.hybrid_search_engine.HybridSearchEngine._merge_results (score 0.26)
   Evidence: Score 0.26, Merge and deduplicate keyword and vector results
4) app/core/langgraph/tools/ccnl_tool.py:83 — app.core.langgraph.tools.ccnl_tool.CCNLTool.__init__ (score 0.25)
   Evidence: Score 0.25, method: __init__
5) app/core/langgraph/tools/ccnl_tool.py:101 — app.core.langgraph.tools.ccnl_tool.CCNLTool._run (score 0.25)
   Evidence: Score 0.25, Execute CCNL query (synchronous version).

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToolResults
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->