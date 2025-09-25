# RAG STEP 86 — Return tool error Invalid file (RAG.platform.return.tool.error.invalid.file)

**Type:** error  
**Category:** platform  
**Node ID:** `ToolErr`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolErr` (Return tool error Invalid file).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ✅ Implemented
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
  `RAG STEP 86 (RAG.platform.return.tool.error.invalid.file): Return tool error Invalid file | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.21

Top candidates:
1) app/orchestrators/platform.py:2178 — app.orchestrators.platform.step_86__tool_error (score 0.21)
   Evidence: Score 0.21, RAG STEP 86 — Return tool error Invalid file
ID: RAG.platform.return.tool.error....
2) app/orchestrators/platform.py:2491 — app.orchestrators.platform._handle_tool_results_error (score 0.21)
   Evidence: Score 0.21, Handle errors in tool results processing with graceful fallback.
3) app/orchestrators/response.py:402 — app.orchestrators.response._handle_return_complete_error (score 0.21)
   Evidence: Score 0.21, Handle errors in ChatResponse formatting with graceful fallback.
4) app/orchestrators/routing.py:271 — app.orchestrators.routing._handle_tool_type_error (score 0.21)
   Evidence: Score 0.21, Handle errors in tool type detection with graceful fallback.
5) app/services/italian_tax_calculator.py:68 — app.services.italian_tax_calculator.InvalidIncomeError (score 0.20)
   Evidence: Score 0.20, Raised when income value is invalid.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for ToolErr
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->