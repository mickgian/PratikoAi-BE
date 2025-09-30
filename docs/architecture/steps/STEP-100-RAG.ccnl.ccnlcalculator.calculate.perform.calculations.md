# RAG STEP 100 — CCNLCalculator.calculate Perform calculations (RAG.ccnl.ccnlcalculator.calculate.perform.calculations)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLCalc`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLCalc` (CCNLCalculator.calculate Perform calculations).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/ccnl.py:99` - `step_100__ccnlcalc()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator performing CCNL (Italian labor agreement) calculations. Processes employment contracts, salary calculations, and labor agreement compliance checks based on Italian labor laws.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - graceful degradation with existing error handling

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 100 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.46

Top candidates:
1) app/models/ccnl_data.py:715 — app.models.ccnl_data.CCNLCalculator.__init__ (score 0.46)
   Evidence: Score 0.46, Initialize calculator with CCNL agreement.
2) app/services/ccnl_calculator_engine.py:1 — app.services.ccnl_calculator_engine (score 0.45)
   Evidence: Score 0.45, CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agree...
3) app/orchestrators/ccnl.py:14 — app.orchestrators.ccnl.step_81__ccnlquery (score 0.44)
   Evidence: Score 0.44, RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements
ID: RAG.ccnl.ccnltool.c...
4) app/orchestrators/ccnl.py:166 — app.orchestrators.ccnl._perform_ccnl_calculations (score 0.43)
   Evidence: Score 0.43, Perform CCNL calculations using the enhanced calculation engine.

Delegates to E...
5) app/core/langgraph/tools/ccnl_tool.py:64 — app.core.langgraph.tools.ccnl_tool.CCNLTool (score 0.40)
   Evidence: Score 0.40, LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->