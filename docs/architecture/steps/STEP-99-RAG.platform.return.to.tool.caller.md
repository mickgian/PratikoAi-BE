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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/facts.py:675 — app.orchestrators.facts.step_98__to_tool_results (score 0.30)
   Evidence: Score 0.30, RAG STEP 98 — Convert to ToolMessage facts and spans
ID: RAG.facts.convert.to.to...
2) app/orchestrators/platform.py:2245 — app.orchestrators.platform.step_99__tool_results (score 0.30)
   Evidence: Score 0.30, RAG STEP 99 — Return to tool caller
ID: RAG.platform.return.to.tool.caller
Type:...
3) app/orchestrators/kb.py:32 — app.orchestrators.kb.step_80__kbquery_tool (score 0.26)
   Evidence: Score 0.26, RAG STEP 80 — KnowledgeSearchTool.search KB on demand
ID: RAG.kb.knowledgesearch...
4) evals/helpers.py:129 — evals.helpers.process_trace_results (score 0.26)
   Evidence: Score 0.26, Process results for a single trace.

Args:
    report: The report dictionary.
  ...
5) app/orchestrators/cache.py:654 — app.orchestrators.cache.step_66__return_cached (score 0.26)
   Evidence: Score 0.26, RAG STEP 66 — Return cached response
ID: RAG.cache.return.cached.response
Type: ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToolResults
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->