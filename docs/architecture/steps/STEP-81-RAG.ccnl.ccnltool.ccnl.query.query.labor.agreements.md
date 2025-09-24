# RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLQuery` (CCNLTool.ccnl_query Query labor agreements).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/ccnl.py:step_81__ccnlquery`, `app/core/langgraph/tools/ccnl_tool.py:CCNLTool`
- **Status:** ✅ Implemented
- **Behavior notes:** Thin async orchestrator that executes on-demand CCNL (Italian Collective Labor Agreement) queries when the LLM calls the CCNLTool. Uses CCNLTool for querying labor agreements, salary calculations, leave entitlements, and compliance information. Routes to Step 99 (ToolResults). Note: Mermaid shows CCNLQuery → PostgresQuery → CCNLCalc → ToolResults, but implementation collapses internal steps as CCNLTool handles PostgreSQL queries and calculations internally.

## Differences (Blueprint vs Current)
- Mermaid diagram shows intermediate steps (PostgresQuery and CCNLCalc) but implementation collapses these into CCNLTool's internal logic - this is acceptable as the orchestrator provides the same external behavior

## Risks / Impact
- None - uses existing CCNLTool infrastructure with comprehensive test coverage

## TDD Task List
- [x] Unit tests (CCNL query execution, search queries, salary calculation, leave calculation, metadata, routing, context preservation, error handling)
- [x] Integration tests (Step 79→81→99 flow, Step 99 preparation)
- [x] Implementation changes (thin async orchestrator wrapping CCNLTool)
- [x] Observability: add structured log line
  `RAG STEP 81 (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements): CCNLTool.ccnl_query Query labor agreements | attrs={...}`
- [x] Feature flag / config if needed (uses existing CCNLTool configuration)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ✅  |  Confidence: 1.00

Top candidates:
1) app/orchestrators/ccnl.py:14 — app.orchestrators.ccnl.step_81__ccnlquery (score 1.00)
   Evidence: Score 1.00, RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements
ID: RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements
Type: process
2) app/core/langgraph/tools/ccnl_tool.py:64 — app.core.langgraph.tools.ccnl_tool.CCNLTool (score 0.95)
   Evidence: Score 0.95, LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data.
3) app/services/ccnl_calculator_engine.py:1 — app.services.ccnl_calculator_engine (score 0.85)
   Evidence: Score 0.85, CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agreements.

Notes:
- ✅ Implementation complete and wired correctly
- ✅ Async orchestrator wrapping CCNLTool
- ✅ CCNLTool already exists in LangGraph tools
- ✅ 12/12 tests passing
- ✅ Routes to Step 99 (ToolResults) per Mermaid
- ✅ Handles PostgresQuery and CCNLCalc internally (Steps 82 and 100 collapsed into CCNLTool)

Completed TDD actions:
- ✅ Created thin async orchestrator in app/orchestrators/ccnl.py
- ✅ Integrated with existing CCNLTool
- ✅ Implemented 12 comprehensive tests (unit + parity + integration)
- ✅ Added structured observability logging
- ✅ Verified error handling and edge cases
<!-- AUTO-AUDIT:END -->