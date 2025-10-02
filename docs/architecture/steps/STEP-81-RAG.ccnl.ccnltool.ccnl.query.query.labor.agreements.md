# RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLQuery` (CCNLTool.ccnl_query Query labor agreements).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/ccnl.py:14` - `step_81__ccnlquery()`
- **Role:** Node
- **Status:** missing
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
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.47

Top candidates:
1) app/orchestrators/ccnl.py:14 — app.orchestrators.ccnl.step_81__ccnlquery (score 0.47)
   Evidence: Score 0.47, RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements
ID: RAG.ccnl.ccnltool.c...
2) app/services/ccnl_calculator_engine.py:1 — app.services.ccnl_calculator_engine (score 0.46)
   Evidence: Score 0.46, CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agree...
3) app/models/ccnl_data.py:715 — app.models.ccnl_data.CCNLCalculator.__init__ (score 0.44)
   Evidence: Score 0.44, Initialize calculator with CCNL agreement.
4) app/core/langgraph/tools/ccnl_tool.py:64 — app.core.langgraph.tools.ccnl_tool.CCNLTool (score 0.43)
   Evidence: Score 0.43, LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data.
5) app/services/ccnl_service.py:806 — app.services.ccnl_service.CCNLService._convert_external_data_to_agreement (score 0.39)
   Evidence: Score 0.39, Convert external data format to CCNLAgreement.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Node step requires LangGraph wiring to be considered fully implemented

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->