# RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLQuery` (CCNLTool.ccnl_query Query labor agreements).

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
  `RAG STEP 81 (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements): CCNLTool.ccnl_query Query labor agreements | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.46

Top candidates:
1) app/services/ccnl_calculator_engine.py:1 — app.services.ccnl_calculator_engine (score 0.46)
   Evidence: Score 0.46, CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agree...
2) app/models/ccnl_data.py:715 — app.models.ccnl_data.CCNLCalculator.__init__ (score 0.44)
   Evidence: Score 0.44, Initialize calculator with CCNL agreement.
3) app/core/langgraph/tools/ccnl_tool.py:64 — app.core.langgraph.tools.ccnl_tool.CCNLTool (score 0.43)
   Evidence: Score 0.43, LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data.
4) app/services/ccnl_service.py:806 — app.services.ccnl_service.CCNLService._convert_external_data_to_agreement (score 0.39)
   Evidence: Score 0.39, Convert external data format to CCNLAgreement.
5) app/data/ccnl_priority1.py:843 — app.data.ccnl_priority1.get_all_priority1_ccnl_data (score 0.37)
   Evidence: Score 0.37, Get all Priority 1 CCNL agreements.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->