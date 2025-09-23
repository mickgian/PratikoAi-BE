# RAG STEP 76 — Convert to AIMessage with tool_calls (RAG.platform.convert.to.aimessage.with.tool.calls)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertAIMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertAIMsg` (Convert to AIMessage with tool_calls).

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
  `RAG STEP 76 (RAG.platform.convert.to.aimessage.with.tool.calls): Convert to AIMessage with tool_calls | attrs={...}`
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
1) app/orchestrators/kb.py:32 — app.orchestrators.kb.step_80__kbquery_tool (score 0.26)
   Evidence: Score 0.26, RAG STEP 80 — KnowledgeSearchTool.search KB on demand
ID: RAG.kb.knowledgesearch...
2) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.25)
   Evidence: Score 0.25, Convert internal SearchResponse to API model.
3) app/orchestrators/facts.py:421 — app.orchestrators.facts.step_98__to_tool_results (score 0.25)
   Evidence: Score 0.25, RAG STEP 98 — Convert to ToolMessage facts and spans
ID: RAG.facts.convert.to.to...
4) app/orchestrators/platform.py:2245 — app.orchestrators.platform.step_99__tool_results (score 0.25)
   Evidence: Score 0.25, RAG STEP 99 — Return to tool caller
ID: RAG.platform.return.to.tool.caller
Type:...
5) app/orchestrators/routing.py:14 — app.orchestrators.routing.step_79__tool_type (score 0.25)
   Evidence: Score 0.25, RAG STEP 79 — Tool type?
ID: RAG.routing.tool.type
Type: decision | Category: ro...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ConvertAIMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->